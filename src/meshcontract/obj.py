"""Small Wavefront OBJ geometry reader used by the MVP backend."""

from __future__ import annotations

from math import isfinite
from pathlib import Path

from .models import Dimensions, MeshStats


class ObjParseError(ValueError):
    """Raised when an OBJ file cannot be read as valid mesh geometry."""


def _parse_float(value: str, path: Path, line_number: int) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise ObjParseError(f"{path}:{line_number}: invalid vertex coordinate {value!r}") from exc
    if not isfinite(number):
        raise ObjParseError(f"{path}:{line_number}: vertex coordinates must be finite numbers")
    return number


def _parse_face_vertex(token: str, vertex_count: int, path: Path, line_number: int) -> int:
    """Return a zero-based position index; validate optional OBJ index syntax too."""
    fields = token.split("/")
    if len(fields) > 3 or not fields[0]:
        raise ObjParseError(f"{path}:{line_number}: invalid face vertex reference {token!r}")

    indices: list[int] = []
    for field in fields:
        if not field:
            continue
        try:
            index = int(field)
        except ValueError as exc:
            raise ObjParseError(f"{path}:{line_number}: invalid face vertex reference {token!r}") from exc
        if index == 0:
            raise ObjParseError(f"{path}:{line_number}: OBJ indices are one-based; index 0 is invalid")
        indices.append(index)

    position_index = indices[0]
    resolved = position_index - 1 if position_index > 0 else vertex_count + position_index
    if resolved < 0 or resolved >= vertex_count:
        raise ObjParseError(
            f"{path}:{line_number}: vertex index {position_index} is out of range "
            f"for {vertex_count} vertices"
        )
    return resolved


def _validate_face(
    indices: list[int], vertices: list[tuple[float, float, float]],
    path: Path, line_number: int,
) -> None:
    points = [vertices[index] for index in indices]
    if len(set(indices)) != len(indices) or len(set(points)) != len(points):
        raise ObjParseError(f"{path}:{line_number}: a face contains repeated vertices")

    # Finite floats are exact dyadic rationals. A common power-of-two denominator
    # scales every axis uniformly into integers, without rounded subtraction,
    # overflow, underflow, or a geometry tolerance.
    ratios = [[coordinate.as_integer_ratio() for coordinate in point] for point in points]
    denominator = max(denom for point in ratios for _, denom in point)
    exact = [
        tuple(numerator * (denominator // denom) for numerator, denom in point)
        for point in ratios
    ]
    origin = exact[0]
    edges = [tuple(point[j] - origin[j] for j in range(3)) for point in exact[1:]]
    # A polygon is completely degenerate only if every fan triangle is collinear.
    # Do not sum oriented areas: cancellation is not zero referenced geometry.
    for a, b in zip(edges, edges[1:]):
        if any(
            a[(j + 1) % 3] * b[(j + 2) % 3]
            != a[(j + 2) % 3] * b[(j + 1) % 3]
            for j in range(3)
        ):
            return
    raise ObjParseError(f"{path}:{line_number}: a face has zero area (completely degenerate)")


def parse_obj(path: Path | str) -> MeshStats:
    """Read vertices and polygon faces from an OBJ file and calculate mesh metrics.

    Unknown OBJ statements (such as material and smoothing directives) are ignored.
    Positive and relative negative vertex indices are supported.
    """
    obj_path = Path(path)
    vertices: list[tuple[float, float, float]] = []
    face_count = 0
    triangle_count = 0
    ngon_count = 0

    try:
        source = obj_path.open("r", encoding="utf-8-sig")
    except OSError as exc:
        raise ObjParseError(f"cannot read OBJ file {obj_path}: {exc}") from exc

    try:
        with source:
            for line_number, raw_line in enumerate(source, start=1):
                line = raw_line.partition("#")[0].strip()
                if not line:
                    continue
                parts = line.split()
                statement = parts[0]

                if statement == "v":
                    if len(parts) < 4:
                        raise ObjParseError(
                            f"{obj_path}:{line_number}: a vertex must have at least three coordinates"
                        )
                    vertices.append(
                        (
                            _parse_float(parts[1], obj_path, line_number),
                            _parse_float(parts[2], obj_path, line_number),
                            _parse_float(parts[3], obj_path, line_number),
                        )
                    )
                elif statement == "f":
                    polygon_size = len(parts) - 1
                    if polygon_size < 3:
                        raise ObjParseError(
                            f"{obj_path}:{line_number}: a face must reference at least three vertices"
                        )
                    indices = [
                        _parse_face_vertex(token, len(vertices), obj_path, line_number)
                        for token in parts[1:]
                    ]
                    _validate_face(indices, vertices, obj_path, line_number)
                    face_count += 1
                    triangle_count += polygon_size - 2
                    if polygon_size > 4:
                        ngon_count += 1
    except UnicodeDecodeError as exc:
        raise ObjParseError(f"OBJ file is not valid UTF-8: {obj_path}") from exc
    except OSError as exc:
        raise ObjParseError(f"cannot read OBJ file {obj_path}: {exc}") from exc

    if not vertices:
        raise ObjParseError(f"{obj_path}: no vertices found")
    if not face_count:
        raise ObjParseError(f"{obj_path}: no faces found")

    xs = [vertex[0] for vertex in vertices]
    ys = [vertex[1] for vertex in vertices]
    zs = [vertex[2] for vertex in vertices]
    dimensions = Dimensions(
        width_m=max(xs) - min(xs),
        length_m=max(ys) - min(ys),
        height_m=max(zs) - min(zs),
    )
    if not all(isfinite(value) for value in (dimensions.width_m, dimensions.length_m, dimensions.height_m)):
        raise ObjParseError(f"{obj_path}: bounding-box dimensions exceed the finite numeric range")
    return MeshStats(
        vertices=len(vertices),
        faces=face_count,
        triangles=triangle_count,
        dimensions=dimensions,
        ngon_faces=ngon_count,
    )
