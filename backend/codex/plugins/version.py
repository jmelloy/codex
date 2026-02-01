"""Semantic versioning and version constraint utilities for plugins.

This module provides version parsing, comparison, and constraint matching
following the semver specification (https://semver.org/).

Version constraints support:
- Exact match: "1.0.0"
- Greater than: ">1.0.0"
- Greater than or equal: ">=1.0.0"
- Less than: "<2.0.0"
- Less than or equal: "<=2.0.0"
- Caret (compatible with): "^1.2.3" (>=1.2.3, <2.0.0)
- Tilde (approximately): "~1.2.3" (>=1.2.3, <1.3.0)
- Range: ">=1.0.0,<2.0.0"
- Wildcard: "1.x" or "1.*" (>=1.0.0, <2.0.0)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import Any


@total_ordering
@dataclass
class Version:
    """Represents a semantic version (major.minor.patch[-prerelease][+build])."""

    major: int
    minor: int
    patch: int
    prerelease: str | None = None
    build: str | None = None

    # Regex pattern for parsing semver strings
    SEMVER_PATTERN = re.compile(
        r"^v?"  # Optional 'v' prefix
        r"(?P<major>0|[1-9]\d*)"
        r"\.(?P<minor>0|[1-9]\d*)"
        r"\.(?P<patch>0|[1-9]\d*)"
        r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
        r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
        r"$"
    )

    @classmethod
    def parse(cls, version_str: str) -> Version:
        """Parse a version string into a Version object.

        Args:
            version_str: Version string (e.g., "1.2.3", "1.0.0-alpha", "v2.0.0+build.123")

        Returns:
            Version object

        Raises:
            ValueError: If the version string is invalid
        """
        match = cls.SEMVER_PATTERN.match(version_str.strip())
        if not match:
            raise ValueError(f"Invalid semantic version: {version_str}")

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("prerelease"),
            build=match.group("build"),
        )

    @classmethod
    def try_parse(cls, version_str: str) -> Version | None:
        """Try to parse a version string, returning None on failure.

        Args:
            version_str: Version string to parse

        Returns:
            Version object or None if parsing fails
        """
        try:
            return cls.parse(version_str)
        except ValueError:
            return None

    def __str__(self) -> str:
        """Return the string representation of the version."""
        result = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            result += f"-{self.prerelease}"
        if self.build:
            result += f"+{self.build}"
        return result

    def __repr__(self) -> str:
        """Return a debug representation of the version."""
        return f"Version({self})"

    def __hash__(self) -> int:
        """Return hash for use in sets and dicts."""
        return hash((self.major, self.minor, self.patch, self.prerelease))

    def _compare_tuple(self) -> tuple[int, int, int, bool, list[str | int]]:
        """Return a tuple for comparison.

        Prerelease versions have lower precedence than normal versions.
        """
        # Prerelease identifiers are compared as follows:
        # 1. Identifiers consisting of only digits are compared numerically
        # 2. Identifiers with letters or hyphens are compared lexically
        # 3. Numeric identifiers have lower precedence than non-numeric
        prerelease_parts: list[str | int] = []
        if self.prerelease:
            for part in self.prerelease.split("."):
                if part.isdigit():
                    prerelease_parts.append(int(part))
                else:
                    prerelease_parts.append(part)

        # Versions with prerelease have lower precedence
        has_prerelease = self.prerelease is not None

        return (self.major, self.minor, self.patch, not has_prerelease, prerelease_parts)

    def __eq__(self, other: object) -> bool:
        """Check equality (build metadata is ignored per semver spec)."""
        if not isinstance(other, Version):
            return NotImplemented
        return self._compare_tuple() == other._compare_tuple()

    def __lt__(self, other: Version) -> bool:
        """Check if this version is less than another."""
        if not isinstance(other, Version):
            return NotImplemented

        self_tuple = self._compare_tuple()
        other_tuple = other._compare_tuple()

        # Compare major.minor.patch and has_prerelease
        if self_tuple[:4] != other_tuple[:4]:
            return self_tuple[:4] < other_tuple[:4]

        # Compare prerelease identifiers
        self_pre = self_tuple[4]
        other_pre = other_tuple[4]

        # If neither has prerelease, they're equal in terms of ordering
        if not self_pre and not other_pre:
            return False

        # Version without prerelease has higher precedence
        if not self_pre:
            return False
        if not other_pre:
            return True

        # Compare prerelease parts
        for s, o in zip(self_pre, other_pre):
            if type(s) != type(o):
                # Numeric has lower precedence than non-numeric
                return isinstance(s, int)
            if s != o:
                return s < o

        # Shorter prerelease has lower precedence
        return len(self_pre) < len(other_pre)

    def bump_major(self) -> Version:
        """Return a new version with major incremented."""
        return Version(self.major + 1, 0, 0)

    def bump_minor(self) -> Version:
        """Return a new version with minor incremented."""
        return Version(self.major, self.minor + 1, 0)

    def bump_patch(self) -> Version:
        """Return a new version with patch incremented."""
        return Version(self.major, self.minor, self.patch + 1)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary representation."""
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "prerelease": self.prerelease,
            "build": self.build,
            "string": str(self),
        }


class VersionConstraint:
    """Represents a version constraint that can match against versions.

    Supports various constraint formats:
    - Exact: "1.0.0"
    - Comparison: ">1.0.0", ">=1.0.0", "<2.0.0", "<=2.0.0"
    - Caret: "^1.2.3" (compatible changes)
    - Tilde: "~1.2.3" (patch-level changes)
    - Wildcard: "1.x", "1.*", "1.2.x"
    - Range: ">=1.0.0,<2.0.0"
    """

    def __init__(self, constraint_str: str):
        """Initialize a version constraint.

        Args:
            constraint_str: Constraint string (e.g., ">=1.0.0", "^2.0.0")
        """
        self.original = constraint_str.strip()
        self._matchers: list[tuple[str, Version | None, Version | None]] = []
        self._parse_constraint(self.original)

    def _parse_constraint(self, constraint_str: str) -> None:
        """Parse the constraint string into matchers."""
        # Handle multiple constraints separated by comma or space
        parts = re.split(r"[,\s]+", constraint_str)
        parts = [p.strip() for p in parts if p.strip()]

        for part in parts:
            self._parse_single_constraint(part)

    def _parse_single_constraint(self, constraint: str) -> None:
        """Parse a single constraint part."""
        constraint = constraint.strip()

        if not constraint:
            return

        # Wildcard patterns: 1.x, 1.*, 1.2.x, *
        wildcard_match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.[x*]|\.[x*]\.[x*])?$|^[x*]$", constraint)
        if wildcard_match:
            if constraint in ("*", "x"):
                # Match any version
                self._matchers.append(("any", None, None))
                return

            groups = wildcard_match.groups()
            major = int(groups[0]) if groups[0] else 0
            minor = int(groups[1]) if groups[1] else None

            if minor is not None:
                # 1.2.x means >=1.2.0, <1.3.0
                min_ver = Version(major, minor, 0)
                max_ver = Version(major, minor + 1, 0)
            else:
                # 1.x means >=1.0.0, <2.0.0
                min_ver = Version(major, 0, 0)
                max_ver = Version(major + 1, 0, 0)

            self._matchers.append(("range", min_ver, max_ver))
            return

        # Caret: ^1.2.3 means >=1.2.3, <2.0.0 (or <0.2.0 for ^0.1.x)
        if constraint.startswith("^"):
            version = Version.parse(constraint[1:])
            min_ver = version
            if version.major == 0:
                if version.minor == 0:
                    # ^0.0.x means =0.0.x (exact)
                    max_ver = Version(0, 0, version.patch + 1)
                else:
                    # ^0.x.y means >=0.x.y, <0.(x+1).0
                    max_ver = Version(0, version.minor + 1, 0)
            else:
                # ^x.y.z means >=x.y.z, <(x+1).0.0
                max_ver = Version(version.major + 1, 0, 0)
            self._matchers.append(("range", min_ver, max_ver))
            return

        # Tilde: ~1.2.3 means >=1.2.3, <1.3.0
        if constraint.startswith("~"):
            version = Version.parse(constraint[1:])
            min_ver = version
            max_ver = Version(version.major, version.minor + 1, 0)
            self._matchers.append(("range", min_ver, max_ver))
            return

        # Comparison operators
        match = re.match(r"^(>=|<=|>|<|=)?(.+)$", constraint)
        if match:
            op = match.group(1) or "="
            version_str = match.group(2)
            version = Version.parse(version_str)
            self._matchers.append((op, version, None))
            return

        raise ValueError(f"Invalid version constraint: {constraint}")

    def matches(self, version: Version | str) -> bool:
        """Check if a version matches this constraint.

        Args:
            version: Version object or string to check

        Returns:
            True if the version matches all constraint parts
        """
        if isinstance(version, str):
            version = Version.parse(version)

        for op, min_ver, max_ver in self._matchers:
            if op == "any":
                continue
            elif op == "range":
                if not (min_ver <= version < max_ver):
                    return False
            elif op == "=":
                if version != min_ver:
                    return False
            elif op == ">":
                if not (version > min_ver):
                    return False
            elif op == ">=":
                if not (version >= min_ver):
                    return False
            elif op == "<":
                if not (version < min_ver):
                    return False
            elif op == "<=":
                if not (version <= min_ver):
                    return False

        return True

    def __str__(self) -> str:
        """Return the original constraint string."""
        return self.original

    def __repr__(self) -> str:
        """Return a debug representation."""
        return f"VersionConstraint({self.original!r})"


@dataclass
class Dependency:
    """Represents a plugin dependency."""

    plugin_id: str
    constraint: VersionConstraint
    optional: bool = False

    @classmethod
    def parse(cls, dep_str: str | dict[str, Any]) -> Dependency:
        """Parse a dependency from string or dict format.

        String format: "plugin-id" or "plugin-id@>=1.0.0"
        Dict format: {"plugin_id": "...", "version": ">=1.0.0", "optional": false}

        Args:
            dep_str: Dependency specification

        Returns:
            Dependency object
        """
        if isinstance(dep_str, dict):
            plugin_id = dep_str.get("plugin_id") or dep_str.get("id")
            if not plugin_id:
                raise ValueError("Dependency dict must have 'plugin_id' or 'id' field")
            version = dep_str.get("version", "*")
            optional = dep_str.get("optional", False)
            return cls(
                plugin_id=plugin_id,
                constraint=VersionConstraint(version),
                optional=optional,
            )

        # String format: "plugin-id" or "plugin-id@>=1.0.0"
        if "@" in dep_str:
            parts = dep_str.split("@", 1)
            plugin_id = parts[0].strip()
            version = parts[1].strip()
        else:
            plugin_id = dep_str.strip()
            version = "*"

        return cls(
            plugin_id=plugin_id,
            constraint=VersionConstraint(version),
            optional=False,
        )

    def is_satisfied_by(self, version: Version | str) -> bool:
        """Check if a version satisfies this dependency.

        Args:
            version: Version to check

        Returns:
            True if the version satisfies the constraint
        """
        return self.constraint.matches(version)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary representation."""
        return {
            "plugin_id": self.plugin_id,
            "version": str(self.constraint),
            "optional": self.optional,
        }

    def __str__(self) -> str:
        """Return string representation."""
        suffix = " (optional)" if self.optional else ""
        return f"{self.plugin_id}@{self.constraint}{suffix}"

    def __repr__(self) -> str:
        """Return debug representation."""
        return f"Dependency({self.plugin_id!r}, {self.constraint!r}, optional={self.optional})"


# Current Codex version - should be updated with each release
CODEX_VERSION = Version(1, 0, 0)


def get_codex_version() -> Version:
    """Get the current Codex version.

    Returns:
        Current Codex version
    """
    return CODEX_VERSION


def check_codex_compatibility(constraint_str: str) -> bool:
    """Check if a codex_version constraint is compatible with the current version.

    Args:
        constraint_str: Version constraint string (e.g., ">=1.0.0")

    Returns:
        True if the current Codex version satisfies the constraint
    """
    if not constraint_str:
        return True

    constraint = VersionConstraint(constraint_str)
    return constraint.matches(CODEX_VERSION)
