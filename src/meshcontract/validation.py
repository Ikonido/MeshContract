"""Core contract checks, independent of the source model format."""

from __future__ import annotations

from .contract import Contract
from .models import MeshStats, ValidationResult, Violation


def evaluate_mesh(stats: MeshStats, contract: Contract) -> ValidationResult:
    """Validate backend-independent geometry metrics against a contract."""
    violations: list[Violation] = []

    if contract.max_triangles is not None and stats.triangles > contract.max_triangles:
        violations.append(
            Violation(
                code="max_triangles_exceeded",
                rule="max_triangles",
                message=(
                    f"max_triangles exceeded: {stats.triangles} > "
                    f"{contract.max_triangles}"
                ),
                actual=stats.triangles,
                limit=contract.max_triangles,
            )
        )
    if contract.max_vertices is not None and stats.vertices > contract.max_vertices:
        violations.append(
            Violation(
                code="max_vertices_exceeded",
                rule="max_vertices",
                message=(
                    f"max_vertices exceeded: {stats.vertices} > "
                    f"{contract.max_vertices}"
                ),
                actual=stats.vertices,
                limit=contract.max_vertices,
            )
        )

    dimensions = (
        ("max_width_m", stats.dimensions.width_m, contract.max_width_m),
        ("max_height_m", stats.dimensions.height_m, contract.max_height_m),
        ("max_length_m", stats.dimensions.length_m, contract.max_length_m),
    )
    for name, actual, limit in dimensions:
        if limit is not None and actual > limit:
            violations.append(
                Violation(
                    code=f"{name}_exceeded",
                    rule=name,
                    message=f"{name} exceeded: {actual:.3f} m > {limit:.3f} m",
                    actual=actual,
                    limit=limit,
                )
            )

    if not contract.allow_ngons and stats.ngon_faces:
        violations.append(
            Violation(
                code="ngons_not_allowed",
                rule="allow_ngons",
                message=(
                    "allow_ngons is false, but the model contains "
                    f"{stats.ngon_faces} n-gon face(s) (more than four vertices)"
                ),
                actual=stats.ngon_faces,
                limit=0,
            )
        )

    return ValidationResult(metrics=stats, violations=tuple(violations))


def validate_mesh(stats: MeshStats, contract: Contract) -> list[str]:
    """Return the v0.1-compatible human-readable violation messages."""
    return [violation.message for violation in evaluate_mesh(stats, contract).violations]
