"""Core contract checks, independent of the source model format."""

from __future__ import annotations

from .contract import Contract
from .obj import MeshStats


def validate_mesh(stats: MeshStats, contract: Contract) -> list[str]:
    """Return human-readable violations; an empty list means the contract passes."""
    violations: list[str] = []

    if contract.max_triangles is not None and stats.triangles > contract.max_triangles:
        violations.append(
            f"max_triangles exceeded: {stats.triangles} > {contract.max_triangles}"
        )
    if contract.max_vertices is not None and stats.vertices > contract.max_vertices:
        violations.append(f"max_vertices exceeded: {stats.vertices} > {contract.max_vertices}")

    dimensions = (
        ("max_width_m", stats.dimensions.width_m, contract.max_width_m),
        ("max_height_m", stats.dimensions.height_m, contract.max_height_m),
        ("max_length_m", stats.dimensions.length_m, contract.max_length_m),
    )
    for name, actual, limit in dimensions:
        if limit is not None and actual > limit:
            violations.append(f"{name} exceeded: {actual:.3f} m > {limit:.3f} m")

    if not contract.allow_ngons and stats.ngon_faces:
        violations.append(
            "allow_ngons is false, but the model contains "
            f"{stats.ngon_faces} n-gon face(s) (more than four vertices)"
        )

    return violations
