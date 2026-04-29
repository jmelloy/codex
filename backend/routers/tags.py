from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List

import models
import schemas
from database import get_db

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=List[schemas.Tag])
def list_tags(db: Session = Depends(get_db)):
    tags = db.query(models.Tag).all()
    result = []
    for tag in tags:
        count = len(tag.images)
        result.append(schemas.Tag(id=tag.id, name=tag.name, image_count=count))
    return result


@router.delete("/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.delete(tag)
    db.commit()
    return {"deleted": tag_id}


@router.get("/images/{image_id}/tags", response_model=List[schemas.Tag])
def get_image_tags(image_id: int, db: Session = Depends(get_db)):
    img = db.query(models.Image).filter(models.Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return [schemas.Tag(id=t.id, name=t.name, image_count=len(t.images)) for t in img.tags]
