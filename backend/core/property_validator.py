"""Property validation helpers for dynamic views."""

from typing import Any


class PropertyValidator:
    """Validator for file properties."""

    @staticmethod
    def validate_property_schema(properties: dict[str, Any], schema: dict[str, dict[str, Any]]) -> tuple[bool, list[str]]:
        """Validate properties against a schema.

        Args:
            properties: Dictionary of properties to validate
            schema: Schema definition with field names and validation rules
                   Example: {"status": {"type": "string", "enum": ["todo", "done"]}}

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []

        for field_name, rules in schema.items():
            # Check required fields
            if rules.get("required", False) and field_name not in properties:
                errors.append(f"Required field '{field_name}' is missing")
                continue

            # Skip validation if field not present and not required
            if field_name not in properties:
                continue

            value = properties[field_name]

            # Type validation
            if "type" in rules:
                expected_type = rules["type"]
                if not PropertyValidator._check_type(value, expected_type):
                    errors.append(f"Field '{field_name}' should be of type {expected_type}")

            # Enum validation
            if "enum" in rules and value not in rules["enum"]:
                errors.append(f"Field '{field_name}' must be one of {rules['enum']}")

            # Min/max validation for numbers
            if "min" in rules and isinstance(value, (int, float)) and value < rules["min"]:
                errors.append(f"Field '{field_name}' must be at least {rules['min']}")

            if "max" in rules and isinstance(value, (int, float)) and value > rules["max"]:
                errors.append(f"Field '{field_name}' must be at most {rules['max']}")

            # Pattern validation for strings
            if "pattern" in rules and isinstance(value, str):
                import re

                if not re.match(rules["pattern"], value):
                    errors.append(f"Field '{field_name}' does not match pattern {rules['pattern']}")

        return len(errors) == 0, errors

    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        """Check if value matches expected type.

        Args:
            value: Value to check
            expected_type: Expected type name

        Returns:
            True if type matches
        """
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        if expected_type not in type_map:
            return True  # Unknown type, skip validation

        return isinstance(value, type_map[expected_type])

    @staticmethod
    def validate_view_definition(view_def: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a view definition structure.

        Args:
            view_def: View definition dictionary from frontmatter

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []

        # Required top-level fields
        if "type" not in view_def or view_def["type"] != "view":
            errors.append("View definition must have type='view'")

        if "view_type" not in view_def:
            errors.append("View definition must have 'view_type' field")

        # Valid view types
        valid_view_types = ["kanban", "gallery", "rollup", "dashboard", "corkboard", "calendar", "task-list"]
        if "view_type" in view_def and view_def["view_type"] not in valid_view_types:
            errors.append(f"view_type must be one of {valid_view_types}")

        # Query validation
        if "query" in view_def:
            query = view_def["query"]
            if not isinstance(query, dict):
                errors.append("query must be an object")
            else:
                # Validate query structure
                valid_query_fields = [
                    "notebook_ids",
                    "paths",
                    "tags",
                    "tags_any",
                    "file_types",
                    "properties",
                    "properties_exists",
                    "created_after",
                    "created_before",
                    "modified_after",
                    "modified_before",
                    "date_property",
                    "date_after",
                    "date_before",
                    "content_search",
                    "sort",
                    "limit",
                    "offset",
                    "group_by",
                ]

                for field in query:
                    if field not in valid_query_fields:
                        errors.append(f"Unknown query field: {field}")

        # Config validation (view-type specific)
        if "config" in view_def:
            view_type = view_def.get("view_type")
            config = view_def["config"]

            if view_type == "kanban":
                if "columns" not in config:
                    errors.append("Kanban view requires 'columns' in config")
                elif not isinstance(config["columns"], list):
                    errors.append("Kanban 'columns' must be an array")

            elif view_type == "dashboard":
                if "layout" not in view_def:
                    errors.append("Dashboard view requires 'layout' field")

        return len(errors) == 0, errors
