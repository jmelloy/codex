"""Tests for database CRUD operations on Base class."""

import pytest

from codex.db.models import (
    Artifact,
    Entry,
    EntryLineage,
    Notebook,
    NotebookTag,
    Page,
    Tag,
    get_session,
    init_db,
)


@pytest.fixture
def db_session(tmp_path):
    """Create a database session for testing."""
    db_path = tmp_path / "test.db"
    engine = init_db(str(db_path))
    session = get_session(engine)
    yield session
    session.close()


class TestForeignKeyIntrospection:
    """Tests for foreign key introspection."""

    def test_notebook_has_no_foreign_keys(self):
        """Notebook should have no foreign keys."""
        fk_info = Notebook.get_foreign_keys()
        assert fk_info == {}

    def test_page_has_notebook_foreign_key(self):
        """Page should have notebook_id foreign key."""
        fk_info = Page.get_foreign_keys()
        assert "notebook_id" in fk_info
        assert fk_info["notebook_id"] == ("notebooks", "id")

    def test_entry_has_page_foreign_key(self):
        """Entry should have page_id foreign key."""
        fk_info = Entry.get_foreign_keys()
        assert "page_id" in fk_info
        assert fk_info["page_id"] == ("pages", "id")

    def test_entry_has_parent_foreign_key(self):
        """Entry should have parent_id foreign key."""
        fk_info = Entry.get_foreign_keys()
        assert "parent_id" in fk_info
        assert fk_info["parent_id"] == ("entries", "id")

    def test_artifact_has_entry_foreign_key(self):
        """Artifact should have entry_id foreign key."""
        fk_info = Artifact.get_foreign_keys()
        assert "entry_id" in fk_info
        assert fk_info["entry_id"] == ("entries", "id")


class TestCreateOperation:
    """Tests for the create operation."""

    def test_create_returns_typed_instance(self, db_session):
        """Create should return an instance of the model type."""
        notebook = Notebook.create(
            db_session,
            validate_fk=False,
            id="nb-test-1",
            title="Test Notebook",
            description="A test notebook",
        )
        db_session.commit()

        assert isinstance(notebook, Notebook)
        assert notebook.id == "nb-test-1"
        assert notebook.title == "Test Notebook"

    def test_create_with_fk_validation_success(self, db_session):
        """Create should succeed when FK references exist."""
        # Create notebook first
        Notebook.create(
            db_session,
            validate_fk=False,
            id="nb-test-2",
            title="Parent Notebook",
        )
        db_session.commit()

        # Create page with FK validation
        page = Page.create(
            db_session,
            validate_fk=True,
            id="page-test-1",
            notebook_id="nb-test-2",
            title="Test Page",
        )
        db_session.commit()

        assert isinstance(page, Page)
        assert page.notebook_id == "nb-test-2"

    def test_create_with_fk_validation_failure(self, db_session):
        """Create should fail when FK references don't exist."""
        with pytest.raises(ValueError) as exc_info:
            Page.create(
                db_session,
                validate_fk=True,
                id="page-test-2",
                notebook_id="nonexistent-nb",
                title="Bad Page",
            )

        assert "Foreign key constraint failed" in str(exc_info.value)
        assert "notebook_id" in str(exc_info.value)

    def test_create_without_fk_validation(self, db_session):
        """Create should skip FK validation when disabled."""
        # This should not raise even though FK doesn't exist
        # (would fail on commit due to SQLite constraint, but not on create)
        page = Page.create(
            db_session,
            validate_fk=False,
            id="page-test-3",
            notebook_id="nonexistent-nb",
            title="Page without validation",
        )
        # Note: Don't commit - just check the object was created
        assert page.notebook_id == "nonexistent-nb"
        db_session.rollback()


class TestGetOperations:
    """Tests for get operations."""

    def test_get_by_id_found(self, db_session):
        """get_by_id should return the instance when found."""
        Notebook.create(
            db_session,
            validate_fk=False,
            id="nb-get-1",
            title="Get Test",
        )
        db_session.commit()

        result = Notebook.get_by_id(db_session, "nb-get-1")

        assert result is not None
        assert isinstance(result, Notebook)
        assert result.id == "nb-get-1"

    def test_get_by_id_not_found(self, db_session):
        """get_by_id should return None when not found."""
        result = Notebook.get_by_id(db_session, "nonexistent")
        assert result is None

    def test_get_all(self, db_session):
        """get_all should return all instances."""
        Notebook.create(
            db_session, validate_fk=False, id="nb-all-1", title="First"
        )
        Notebook.create(
            db_session, validate_fk=False, id="nb-all-2", title="Second"
        )
        db_session.commit()

        results = Notebook.get_all(db_session)

        assert len(results) == 2
        assert all(isinstance(r, Notebook) for r in results)
        titles = {r.title for r in results}
        assert titles == {"First", "Second"}

    def test_find_by_single_filter(self, db_session):
        """find_by should filter by a single column."""
        Notebook.create(
            db_session, validate_fk=False, id="nb-find-1", title="Alpha"
        )
        Notebook.create(
            db_session, validate_fk=False, id="nb-find-2", title="Beta"
        )
        db_session.commit()

        results = Notebook.find_by(db_session, title="Alpha")

        assert len(results) == 1
        assert results[0].title == "Alpha"

    def test_find_by_multiple_filters(self, db_session):
        """find_by should filter by multiple columns."""
        Notebook.create(
            db_session,
            validate_fk=False,
            id="nb-multi-1",
            title="Same",
            description="First",
        )
        Notebook.create(
            db_session,
            validate_fk=False,
            id="nb-multi-2",
            title="Same",
            description="Second",
        )
        db_session.commit()

        results = Notebook.find_by(db_session, title="Same", description="First")

        assert len(results) == 1
        assert results[0].id == "nb-multi-1"

    def test_find_one_by(self, db_session):
        """find_one_by should return a single instance."""
        Notebook.create(
            db_session, validate_fk=False, id="nb-one-1", title="Unique"
        )
        db_session.commit()

        result = Notebook.find_one_by(db_session, title="Unique")

        assert result is not None
        assert isinstance(result, Notebook)
        assert result.title == "Unique"

    def test_find_one_by_not_found(self, db_session):
        """find_one_by should return None when not found."""
        result = Notebook.find_one_by(db_session, title="Nonexistent")
        assert result is None


class TestUpdateOperation:
    """Tests for the update operation."""

    def test_update_returns_self(self, db_session):
        """update should return the updated instance."""
        notebook = Notebook.create(
            db_session,
            validate_fk=False,
            id="nb-update-1",
            title="Original",
            description="Original desc",
        )
        db_session.commit()

        result = notebook.update(
            db_session,
            validate_fk=False,
            title="Updated",
            description="Updated desc",
        )
        db_session.commit()

        assert result is notebook
        assert notebook.title == "Updated"
        assert notebook.description == "Updated desc"

    def test_update_with_fk_validation_success(self, db_session):
        """update should succeed when FK references exist."""
        Notebook.create(
            db_session, validate_fk=False, id="nb-upd-fk-1", title="First"
        )
        Notebook.create(
            db_session, validate_fk=False, id="nb-upd-fk-2", title="Second"
        )
        page = Page.create(
            db_session,
            validate_fk=False,
            id="page-upd-1",
            notebook_id="nb-upd-fk-1",
            title="Page",
        )
        db_session.commit()

        # Update to reference a different notebook
        page.update(db_session, validate_fk=True, notebook_id="nb-upd-fk-2")
        db_session.commit()

        assert page.notebook_id == "nb-upd-fk-2"

    def test_update_with_fk_validation_failure(self, db_session):
        """update should fail when new FK reference doesn't exist."""
        Notebook.create(
            db_session, validate_fk=False, id="nb-upd-fail", title="Notebook"
        )
        page = Page.create(
            db_session,
            validate_fk=False,
            id="page-upd-fail",
            notebook_id="nb-upd-fail",
            title="Page",
        )
        db_session.commit()

        with pytest.raises(ValueError) as exc_info:
            page.update(db_session, validate_fk=True, notebook_id="nonexistent")

        assert "Foreign key constraint failed" in str(exc_info.value)


class TestDeleteOperations:
    """Tests for delete operations."""

    def test_delete_instance(self, db_session):
        """delete should remove the instance."""
        notebook = Notebook.create(
            db_session, validate_fk=False, id="nb-del-1", title="To Delete"
        )
        db_session.commit()

        result = notebook.delete(db_session)
        db_session.commit()

        assert result is True
        assert Notebook.get_by_id(db_session, "nb-del-1") is None

    def test_delete_by_id_found(self, db_session):
        """delete_by_id should remove the instance when found."""
        Notebook.create(
            db_session, validate_fk=False, id="nb-del-2", title="To Delete"
        )
        db_session.commit()

        result = Notebook.delete_by_id(db_session, "nb-del-2")
        db_session.commit()

        assert result is True
        assert Notebook.get_by_id(db_session, "nb-del-2") is None

    def test_delete_by_id_not_found(self, db_session):
        """delete_by_id should return False when not found."""
        result = Notebook.delete_by_id(db_session, "nonexistent")
        assert result is False


class TestForeignKeyValidation:
    """Tests for foreign key validation."""

    def test_validate_foreign_keys_success(self, db_session):
        """validate_foreign_keys should return info when references exist."""
        Notebook.create(
            db_session, validate_fk=False, id="nb-val-1", title="Notebook"
        )
        db_session.commit()

        result = Page.validate_foreign_keys(
            db_session, {"notebook_id": "nb-val-1", "id": "page-1"}
        )

        assert "notebook_id" in result
        assert result["notebook_id"]["exists"] is True
        assert result["notebook_id"]["table"] == "notebooks"

    def test_validate_foreign_keys_failure(self, db_session):
        """validate_foreign_keys should raise when reference doesn't exist."""
        with pytest.raises(ValueError) as exc_info:
            Page.validate_foreign_keys(
                db_session, {"notebook_id": "nonexistent", "id": "page-1"}
            )

        assert "Foreign key constraint failed" in str(exc_info.value)
        assert "notebook_id" in str(exc_info.value)

    def test_validate_foreign_keys_null_value(self, db_session):
        """validate_foreign_keys should skip null FK values."""
        # Entry.parent_id is a nullable FK - should not raise for None
        Notebook.create(
            db_session, validate_fk=False, id="nb-null-fk", title="Notebook"
        )
        Page.create(
            db_session,
            validate_fk=True,
            id="page-null-fk",
            notebook_id="nb-null-fk",
            title="Page",
        )
        db_session.commit()

        # Validate with null parent_id - should not raise
        result = Entry.validate_foreign_keys(
            db_session,
            {"page_id": "page-null-fk", "parent_id": None},
        )

        # Only page_id should be in result since parent_id is None
        assert "page_id" in result
        assert "parent_id" not in result


class TestTagModel:
    """Tests for Tag model CRUD operations."""

    def test_tag_create_with_autoincrement(self, db_session):
        """Tag should work with autoincrement primary key."""
        tag = Tag.create(
            db_session,
            validate_fk=False,
            name="test-tag",
            color="#ff0000",
        )
        db_session.commit()

        assert isinstance(tag, Tag)
        assert tag.name == "test-tag"
        assert tag.id is not None  # Should be auto-assigned

    def test_tag_get_by_id(self, db_session):
        """Tag should be retrievable by auto-generated ID."""
        tag = Tag.create(
            db_session,
            validate_fk=False,
            name="get-tag",
        )
        db_session.commit()
        tag_id = tag.id

        result = Tag.get_by_id(db_session, tag_id)

        assert result is not None
        assert result.name == "get-tag"


class TestCompositePrimaryKey:
    """Tests for models with composite primary keys."""

    def test_get_by_id_with_composite_key(self, db_session):
        """get_by_id should work with composite primary keys."""
        # Create prerequisite data
        Notebook.create(
            db_session, validate_fk=False, id="nb-comp-1", title="Notebook"
        )
        Tag.create(db_session, validate_fk=False, name="comp-tag")
        db_session.commit()

        # Get the tag id (auto-generated)
        tag = Tag.find_one_by(db_session, name="comp-tag")

        # Create NotebookTag with composite PK
        NotebookTag.create(
            db_session,
            validate_fk=False,
            notebook_id="nb-comp-1",
            tag_id=tag.id,
        )
        db_session.commit()

        # Retrieve using composite key as tuple
        result = NotebookTag.get_by_id(db_session, ("nb-comp-1", tag.id))

        assert result is not None
        assert result.notebook_id == "nb-comp-1"
        assert result.tag_id == tag.id

    def test_get_by_id_composite_key_requires_tuple(self, db_session):
        """get_by_id should raise ValueError if composite key is not a tuple."""
        with pytest.raises(ValueError) as exc_info:
            NotebookTag.get_by_id(db_session, "single-value")

        assert "composite primary key" in str(exc_info.value)
        assert "tuple/list" in str(exc_info.value)

    def test_get_by_id_composite_key_wrong_length(self, db_session):
        """get_by_id should raise ValueError if tuple length doesn't match PK columns."""
        with pytest.raises(ValueError) as exc_info:
            NotebookTag.get_by_id(db_session, ("only-one",))

        assert "2 primary key columns" in str(exc_info.value)
        assert "1 values were provided" in str(exc_info.value)

    def test_delete_by_id_with_composite_key(self, db_session):
        """delete_by_id should work with composite primary keys."""
        # Create prerequisite data
        Notebook.create(
            db_session, validate_fk=False, id="nb-del-comp", title="Notebook"
        )
        Tag.create(db_session, validate_fk=False, name="del-comp-tag")
        db_session.commit()

        tag = Tag.find_one_by(db_session, name="del-comp-tag")

        NotebookTag.create(
            db_session,
            validate_fk=False,
            notebook_id="nb-del-comp",
            tag_id=tag.id,
        )
        db_session.commit()

        # Delete using composite key
        result = NotebookTag.delete_by_id(db_session, ("nb-del-comp", tag.id))
        db_session.commit()

        assert result is True
        assert NotebookTag.get_by_id(db_session, ("nb-del-comp", tag.id)) is None

    def test_entry_lineage_composite_key(self, db_session):
        """EntryLineage should work with composite primary key operations."""
        # Create prerequisite data
        Notebook.create(
            db_session, validate_fk=False, id="nb-lineage", title="Notebook"
        )
        Page.create(
            db_session,
            validate_fk=False,
            id="page-lineage",
            notebook_id="nb-lineage",
            title="Page",
        )
        Entry.create(
            db_session,
            validate_fk=False,
            id="entry-parent",
            page_id="page-lineage",
            entry_type="custom",
            title="Parent",
            inputs="{}",
        )
        Entry.create(
            db_session,
            validate_fk=False,
            id="entry-child",
            page_id="page-lineage",
            entry_type="custom",
            title="Child",
            inputs="{}",
        )
        db_session.commit()

        # Create lineage with composite PK
        EntryLineage.create(
            db_session,
            validate_fk=False,
            parent_id="entry-parent",
            child_id="entry-child",
            relationship_type="derives_from",
        )
        db_session.commit()

        # Retrieve and verify
        result = EntryLineage.get_by_id(db_session, ("entry-parent", "entry-child"))
        assert result is not None
        assert result.relationship_type == "derives_from"
