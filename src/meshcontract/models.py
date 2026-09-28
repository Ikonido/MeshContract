"""Backend-independent immutable geometry models shared by readers and validators."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Dimensions:
    """Axis-aligned dimensions, interpreted using the documented XYZ convention."""

    width_m: float
    length_m: float
    height_m: float


@dataclass(frozen=True, slots=True)
class MeshStats:
    """Geometry metrics needed by contract validation."""

    vertices: int
    faces: int
    triangles: int
    dimensions: Dimensions
    ngon_faces: int
