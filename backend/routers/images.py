import math
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session
from PIL import Image as PILImage

import models
import schemas
from database import get_db
from utils.scanner import scan_directory, create_thumbnail, THUMBNAIL_DIR

router = APIRouter(prefix="/api/images", tags=["images"])


def apply_filters(query, db: Session, q, tags, min_rating, show_hidden, date_from, date_to):
    if not show_hidden:
        query = query.filter(models.Image.hidden == False)

    if min_rating is not None and min_rating > -999:
        query = query.filter(models.Image.rating >= min_rating)
    elif not show_hidden:
        # By default hide thumbs-down (rating == -1)
        query = query.filter(models.Image.rating > -1)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                models.Image.filename.ilike(like),
                models.Image.prompt.ilike(like),
                models.Image.description.ilike(like),
                models.Image.sidecar_data.ilike(like),
            )
        )

    if tags:
        for tag_name in tags:
            query = query.filter(
                models.Image.tags.any(models.Tag.name == tag_name)
            )

    if date_from:
        query = query.filter(models.Image.date_taken >= date_from)
    if date_to:
        query = query.filter(models.Image.date_taken <= date_to)

    return query


@router.get("", response_model=schemas.ImageListResponse)
def list_images(
    q: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    min_rating: int = Query(-999),
    show_hidden: bool = Query(False),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("date_taken"),
    sort_dir: str = Query("desc"),
    db: Session = Depends(get_db),
):
    from datetime import datetime

    def parse_dt(s):
        if not s:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                pass
        return None

    date_from_dt = parse_dt(date_from)
    date_to_dt = parse_dt(date_to)

    query = db.query(models.Image)
    query = apply_filters(query, db, q, tags or [], min_rating, show_hidden, date_from_dt, date_to_dt)

    total = query.count()

    sort_column = {
        "date_taken": models.Image.date_taken,
        "created_at": models.Image.created_at,
        "rating": models.Image.rating,
        "filename": models.Image.filename,
    }.get(sort_by, models.Image.date_taken)

    if sort_dir == "asc":
        query = query.order_by(sort_column.asc().nullslast())
    else:
        query = query.order_by(sort_column.desc().nullslast())

    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()
    pages = math.ceil(total / limit) if total > 0 else 1

    return schemas.ImageListResponse(items=items, total=total, page=page, pages=pages)


@router.get("/{image_id}", response_model=schemas.Image)
def get_image(image_id: int, db: Session = Depends(get_db)):
    img = db.query(models.Image).filter(models.Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return img


@router.get("/{image_id}/file")
def serve_image_file(image_id: int, db: Session = Depends(get_db)):
    img = db.query(models.Image).filter(models.Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    if not os.path.exists(img.filepath):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(img.filepath)


@router.get("/{image_id}/thumbnail")
def serve_thumbnail(image_id: int, db: Session = Depends(get_db)):
    img = db.query(models.Image).filter(models.Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    thumb_path = Path(img.thumbnail_path) if img.thumbnail_path else None
    if thumb_path and thumb_path.exists():
        return FileResponse(str(thumb_path), media_type="image/jpeg")

    # Fallback: generate thumbnail on demand
    if not os.path.exists(img.filepath):
        raise HTTPException(status_code=404, detail="Source file not found")

    THUMBNAIL_DIR.mkdir(exist_ok=True)
    thumb_name = f"{Path(img.filepath).stem}_{hash(img.filepath) & 0xFFFFFF:06x}.jpg"
    thumb_path = THUMBNAIL_DIR / thumb_name
    result = create_thumbnail(Path(img.filepath), thumb_path)
    if result:
        img.thumbnail_path = str(thumb_path)
        db.commit()
        return FileResponse(str(thumb_path), media_type="image/jpeg")

    # Last resort: serve original
    return FileResponse(img.filepath)


@router.put("/{image_id}/rating", response_model=schemas.Image)
def update_rating(image_id: int, rating_update: schemas.RatingUpdate, db: Session = Depends(get_db)):
    img = db.query(models.Image).filter(models.Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    img.rating = rating_update.rating
    if rating_update.rating == -1:
        img.hidden = True
    else:
        img.hidden = False
    from datetime import datetime
    img.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(img)
    return img


@router.post("/{image_id}/tags", response_model=schemas.Image)
def add_tags(image_id: int, body: schemas.TagsAddRequest, db: Session = Depends(get_db)):
    img = db.query(models.Image).filter(models.Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    for tag_name in body.tag_names:
        tag_name = tag_name.strip().lower()
        if not tag_name:
            continue
        tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
        if not tag:
            tag = models.Tag(name=tag_name)
            db.add(tag)
            db.flush()
        if tag not in img.tags:
            img.tags.append(tag)

    db.commit()
    db.refresh(img)
    return img


@router.delete("/{image_id}/tags/{tag_name}", response_model=schemas.Image)
def remove_tag(image_id: int, tag_name: str, db: Session = Depends(get_db)):
    img = db.query(models.Image).filter(models.Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
    if tag and tag in img.tags:
        img.tags.remove(tag)
        db.commit()
        db.refresh(img)
    return img


@router.post("/bulk-tag", response_model=dict)
def bulk_tag(body: schemas.BulkTagRequest, db: Session = Depends(get_db)):
    images = db.query(models.Image).filter(models.Image.id.in_(body.image_ids)).all()
    tags = []
    for tag_name in body.tag_names:
        tag_name = tag_name.strip().lower()
        if not tag_name:
            continue
        tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
        if not tag:
            tag = models.Tag(name=tag_name)
            db.add(tag)
            db.flush()
        tags.append(tag)

    for img in images:
        for tag in tags:
            if tag not in img.tags:
                img.tags.append(tag)

    db.commit()
    return {"tagged": len(images), "tags_added": len(tags)}


@router.post("/scan", response_model=dict)
def scan(body: schemas.ScanRequest, db: Session = Depends(get_db)):
    try:
        stats = scan_directory(db, body.directory)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.delete("/{image_id}", response_model=schemas.Image)
def delete_image(image_id: int, db: Session = Depends(get_db)):
    img = db.query(models.Image).filter(models.Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    img.hidden = True
    from datetime import datetime
    img.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(img)
    return img
