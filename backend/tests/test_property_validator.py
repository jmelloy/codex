"""Tests for property validator used in dynamic views."""

from codex.core.property_validator import PropertyValidator


class TestPropertyValidation:
    """Test property schema validation."""

    def test_validate_required_field_present(self):
        """Test validation passes when required field is present."""
        properties = {"status": "todo"}
        schema = {"status": {"required": True, "type": "string"}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_required_field_missing(self):
        """Test validation fails when required field is missing."""
        properties = {}
        schema = {"status": {"required": True, "type": "string"}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is False
        assert len(errors) == 1
        assert "Required field 'status' is missing" in errors[0]

    def test_validate_optional_field_missing(self):
        """Test validation passes when optional field is missing."""
        properties = {}
        schema = {"priority": {"required": False, "type": "string"}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_string_type(self):
        """Test validation of string type."""
        properties = {"name": "John"}
        schema = {"name": {"type": "string"}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True

        # Test with wrong type
        properties = {"name": 123}
        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is False
        assert "should be of type string" in errors[0]

    def test_validate_number_type(self):
        """Test validation of number type."""
        properties = {"score": 95.5}
        schema = {"score": {"type": "number"}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True

        # Test with integer (should also be valid)
        properties = {"score": 100}
        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True

        # Test with wrong type
        properties = {"score": "high"}
        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is False

    def test_validate_integer_type(self):
        """Test validation of integer type."""
        properties = {"count": 42}
        schema = {"count": {"type": "integer"}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True

        # Test with float (should fail)
        properties = {"count": 42.5}
        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is False

    def test_validate_boolean_type(self):
        """Test validation of boolean type."""
        properties = {"completed": True}
        schema = {"completed": {"type": "boolean"}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True

        properties = {"completed": False}
        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True

        # Test with wrong type
        properties = {"completed": "yes"}
        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is False

    def test_validate_array_type(self):
        """Test validation of array type."""
        properties = {"tags": ["python", "testing"]}
        schema = {"tags": {"type": "array"}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True

        # Test with wrong type
        properties = {"tags": "python"}
        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is False

    def test_validate_object_type(self):
        """Test validation of object type."""
        properties = {"metadata": {"author": "John", "version": 1}}
        schema = {"metadata": {"type": "object"}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True

        # Test with wrong type
        properties = {"metadata": "some string"}
        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is False

    def test_validate_enum(self):
        """Test validation of enum values."""
        properties = {"status": "todo"}
        schema = {"status": {"type": "string", "enum": ["todo", "in_progress", "done"]}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True

        # Test with invalid enum value
        properties = {"status": "invalid"}
        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is False
        assert "must be one of" in errors[0]

    def test_validate_min_value(self):
        """Test validation of minimum value for numbers."""
        properties = {"priority": 5}
        schema = {"priority": {"type": "integer", "min": 1}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True

        # Test below minimum
        properties = {"priority": 0}
        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is False
        assert "must be at least 1" in errors[0]

    def test_validate_max_value(self):
        """Test validation of maximum value for numbers."""
        properties = {"priority": 5}
        schema = {"priority": {"type": "integer", "max": 10}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True

        # Test above maximum
        properties = {"priority": 15}
        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is False
        assert "must be at most 10" in errors[0]

    def test_validate_pattern(self):
        """Test validation of string pattern."""
        properties = {"email": "test@example.com"}
        schema = {"email": {"type": "string", "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True

        # Test with invalid pattern
        properties = {"email": "not-an-email"}
        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is False
        assert "does not match pattern" in errors[0]

    def test_validate_multiple_fields(self):
        """Test validation of multiple fields."""
        properties = {
            "status": "todo",
            "priority": 5,
            "completed": False,
        }
        schema = {
            "status": {"required": True, "type": "string", "enum": ["todo", "done"]},
            "priority": {"type": "integer", "min": 1, "max": 10},
            "completed": {"type": "boolean"},
        }

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True

    def test_validate_multiple_errors(self):
        """Test that multiple validation errors are collected."""
        properties = {
            "priority": 15,  # Exceeds max
            "status": "invalid",  # Not in enum
        }
        schema = {
            "status": {"required": True, "type": "string", "enum": ["todo", "done"]},
            "priority": {"required": True, "type": "integer", "max": 10},
            "description": {"required": True, "type": "string"},  # Missing
        }

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is False
        assert len(errors) == 3  # priority exceeds max, status invalid, description missing

    def test_validate_unknown_type(self):
        """Test validation with unknown type (should skip validation)."""
        properties = {"custom": "value"}
        schema = {"custom": {"type": "unknown_type"}}

        is_valid, errors = PropertyValidator.validate_property_schema(properties, schema)
        assert is_valid is True  # Unknown types are skipped


class TestViewDefinitionValidation:
    """Test view definition validation."""

    def test_validate_valid_view_definition(self):
        """Test validation of valid view definition."""
        view_def = {
            "type": "view",
            "view_type": "kanban",
            "query": {"tags": ["project"]},
            "config": {"columns": [{"label": "To Do"}]},
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_type(self):
        """Test validation fails when type is missing."""
        view_def = {
            "view_type": "kanban",
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is False
        assert any("type='view'" in error for error in errors)

    def test_validate_wrong_type(self):
        """Test validation fails when type is not 'view'."""
        view_def = {
            "type": "page",
            "view_type": "kanban",
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is False
        assert any("type='view'" in error for error in errors)

    def test_validate_missing_view_type(self):
        """Test validation fails when view_type is missing."""
        view_def = {
            "type": "view",
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is False
        assert any("view_type" in error for error in errors)

    def test_validate_invalid_view_type(self):
        """Test validation fails when view_type is invalid."""
        view_def = {
            "type": "view",
            "view_type": "invalid_type",
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is False
        assert any("must be one of" in error for error in errors)

    def test_validate_valid_view_types(self):
        """Test all valid view types pass validation."""
        valid_types = ["kanban", "gallery", "rollup", "dashboard", "corkboard", "calendar", "task-list"]

        for view_type in valid_types:
            view_def = {
                "type": "view",
                "view_type": view_type,
            }

            is_valid, errors = PropertyValidator.validate_view_definition(view_def)
            assert is_valid is True, f"View type '{view_type}' should be valid"

    def test_validate_query_structure(self):
        """Test validation of query structure."""
        view_def = {
            "type": "view",
            "view_type": "kanban",
            "query": {
                "tags": ["project"],
                "content_types": ["md"],
                "sort": "created_at desc",
                "limit": 50,
            },
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is True

    def test_validate_invalid_query_field(self):
        """Test validation fails with invalid query field."""
        view_def = {
            "type": "view",
            "view_type": "kanban",
            "query": {
                "invalid_field": "value",
            },
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is False
        assert any("Unknown query field" in error for error in errors)

    def test_validate_query_not_object(self):
        """Test validation fails when query is not an object."""
        view_def = {
            "type": "view",
            "view_type": "kanban",
            "query": "not an object",
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is False
        assert any("query must be an object" in error for error in errors)

    def test_validate_kanban_requires_columns(self):
        """Test validation fails when kanban view lacks columns config."""
        view_def = {
            "type": "view",
            "view_type": "kanban",
            "config": {},
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is False
        assert any("columns" in error for error in errors)

    def test_validate_kanban_columns_must_be_array(self):
        """Test validation fails when kanban columns is not an array."""
        view_def = {
            "type": "view",
            "view_type": "kanban",
            "config": {"columns": "not an array"},
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is False
        assert any("columns' must be an array" in error for error in errors)

    def test_validate_dashboard_requires_layout(self):
        """Test validation fails when dashboard view lacks layout."""
        view_def = {
            "type": "view",
            "view_type": "dashboard",
            "config": {},  # Config present but no layout
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is False
        assert any("layout" in error for error in errors)

    def test_validate_all_query_fields(self):
        """Test validation of all valid query fields."""
        view_def = {
            "type": "view",
            "view_type": "gallery",
            "query": {
                "notebook_ids": [1, 2],
                "paths": ["*.jpg"],
                "tags": ["photo"],
                "tags_any": ["vacation", "family"],
                "content_types": ["jpg", "png"],
                "properties": {"camera": "Canon"},
                "properties_exists": ["location"],
                "created_after": "2024-01-01",
                "created_before": "2024-12-31",
                "modified_after": "2024-06-01",
                "modified_before": "2024-12-31",
                "date_property": "taken_at",
                "date_after": "2024-01-01",
                "date_before": "2024-12-31",
                "content_search": "vacation",
                "sort": "created_at desc",
                "limit": 100,
                "offset": 0,
                "group_by": "properties.location",
            },
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_view_without_query(self):
        """Test validation passes when query is optional."""
        view_def = {
            "type": "view",
            "view_type": "gallery",
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is True

    def test_validate_view_without_config(self):
        """Test validation passes when config is optional (for non-kanban/dashboard)."""
        view_def = {
            "type": "view",
            "view_type": "gallery",
        }

        is_valid, errors = PropertyValidator.validate_view_definition(view_def)
        assert is_valid is True
