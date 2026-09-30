"""Loading and validating the versioned YAML contract format."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

import yaml


class ContractError(ValueError):
    """Raised for unreadable, invalid, or unsupported contract files."""


class _ContractLoader(yaml.SafeLoader):
    """Reject duplicate explicit keys without changing YAML merge semantics."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict:
        if isinstance(node, yaml.MappingNode):
            seen = set()
            for key_node, _ in node.value:
                if key_node.tag == "tag:yaml.org,2002:merge":
                    continue
                key = self.construct_object(key_node, deep=True)
                try:
                    duplicate = key in seen
                    seen.add(key)
                except TypeError as exc:
                    raise yaml.constructor.ConstructorError(
                        "while reading a contract mapping", node.start_mark,
                        "mapping keys must be hashable", key_node.start_mark,
                    ) from exc
                if duplicate:
                    raise yaml.constructor.ConstructorError(
                        "while reading a contract mapping", node.start_mark,
                        f"duplicate key {key!r}", key_node.start_mark,
                    )
        return super().construct_mapping(node, deep=deep)


@dataclass(frozen=True, slots=True)
class Contract:
    version: int
    max_triangles: int | None = None
    max_vertices: int | None = None
    max_width_m: float | None = None
    max_height_m: float | None = None
    max_length_m: float | None = None
    allow_ngons: bool = True


_ROOT_KEYS = frozenset({"version", "geometry"})
_GEOMETRY_KEYS = frozenset({
    "max_triangles",
    "max_vertices",
    "max_width_m",
    "max_height_m",
    "max_length_m",
    "allow_ngons",
})


def _require_mapping(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{where} must be a YAML mapping")
    if any(not isinstance(key, str) for key in value):
        raise ContractError(f"{where} keys must be strings")
    return value


def _optional_count(geometry: dict[str, Any], key: str) -> int | None:
    value = geometry.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"geometry.{key} must be a non-negative integer")
    if value < 0:
        raise ContractError(f"geometry.{key} must be a non-negative integer")
    return value


def _optional_dimension(geometry: dict[str, Any], key: str) -> float | None:
    value = geometry.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"geometry.{key} must be a finite non-negative number")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ContractError(
            f"geometry.{key} must be a finite non-negative number"
        ) from exc
    if not isfinite(number) or number < 0:
        raise ContractError(f"geometry.{key} must be a finite non-negative number")
    return number


def load_contract(path: Path | str) -> Contract:
    """Load a v1 MeshContract YAML document and reject unsupported fields."""
    contract_path = Path(path)
    try:
        text = contract_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise ContractError(f"cannot read contract file {contract_path}: {exc}") from exc

    try:
        document = yaml.load(text, Loader=_ContractLoader)
    except yaml.YAMLError as exc:
        raise ContractError(f"invalid YAML in {contract_path}: {exc}") from exc

    root = _require_mapping(document, "contract root")
    unknown_root_keys = set(root) - _ROOT_KEYS
    if unknown_root_keys:
        unknown = ", ".join(sorted(unknown_root_keys))
        raise ContractError(f"unknown contract key(s): {unknown}")

    version = root.get("version")
    if isinstance(version, bool) or version != 1 or not isinstance(version, int):
        raise ContractError("version must be the integer 1")

    if "geometry" not in root:
        raise ContractError("contract must contain a geometry mapping")
    geometry = _require_mapping(root["geometry"], "geometry")
    unknown_geometry_keys = set(geometry) - _GEOMETRY_KEYS
    if unknown_geometry_keys:
        unknown = ", ".join(sorted(unknown_geometry_keys))
        raise ContractError(f"unknown geometry key(s): {unknown}")

    allow_ngons = geometry.get("allow_ngons", True)
    if not isinstance(allow_ngons, bool):
        raise ContractError("geometry.allow_ngons must be true or false")

    return Contract(
        version=version,
        max_triangles=_optional_count(geometry, "max_triangles"),
        max_vertices=_optional_count(geometry, "max_vertices"),
        max_width_m=_optional_dimension(geometry, "max_width_m"),
        max_height_m=_optional_dimension(geometry, "max_height_m"),
        max_length_m=_optional_dimension(geometry, "max_length_m"),
        allow_ngons=allow_ngons,
    )
