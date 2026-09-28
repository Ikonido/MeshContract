"""Backend-independent immutable geometry models shared by readers and validators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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


@dataclass(frozen=True, slots=True)
class Violation:
    """A machine-readable contract violation with a human-readable message."""

    code: str
    rule: str
    message: str
    actual: int | float
    limit: int | float


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Backend-independent outcome of checking geometry metrics."""

    metrics: MeshStats
    violations: tuple[Violation, ...]

    @property
    def status(self) -> Literal["pass", "fail"]:
        """Return the stable, machine-readable validation status."""
        return "fail" if self.violations else "pass"
