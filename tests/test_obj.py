from pathlib import Path

import pytest

from meshcontract.obj import ObjParseError, parse_obj


def test_counts_quads_and_bounding_box(tmp_path: Path) -> None:
    model = tmp_path / "box.obj"
    model.write_text(
        "v 0 0 0\nv 2 0 0\nv 2 4 0\nv 0 4 0\n"
        "v 0 0 3\nv 2 0 3\nv 2 4 3\nv 0 4 3\n"
        "f 1 4 3 2\nf 5 6 7 8\nf 1 2 6 5\n"
        "f 2 3 7 6\nf 3 4 8 7\nf 4 1 5 8\n",
        encoding="utf-8",
    )

    stats = parse_obj(model)

    assert stats.vertices == 8
    assert stats.faces == 6
    assert stats.triangles == 12
    assert stats.dimensions.width_m == 2
    assert stats.dimensions.length_m == 4
    assert stats.dimensions.height_m == 3
    assert stats.ngon_faces == 0


def test_negative_indices_and_ngons(tmp_path: Path) -> None:
    model = tmp_path / "pentagon.obj"
    model.write_text(
        "v 0 0 0\nv 1 0 0\nv 2 1 0\nv 1 2 0\nv 0 1 0\nf -5 -4 -3 -2 -1\n",
        encoding="utf-8",
    )

    stats = parse_obj(model)

    assert stats.faces == 1
    assert stats.triangles == 3
    assert stats.ngon_faces == 1


@pytest.mark.parametrize(
    "content, message",
    [
        ("v 0 1\n", "at least three coordinates"),
        ("v 0 0 0\nv 1 0 0\nv 0 1 0\n", "no faces found"),
        ("v 0 0 0\nf 1 2\n", "at least three vertices"),
        ("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 0 1 2\n", "index 0 is invalid"),
        ("v 0 0 0\nf 1 2 3\n", "out of range"),
        ("v nan 0 0\n", "finite numbers"),
    ],
)
def test_malformed_obj_reports_line_context(
    tmp_path: Path, content: str, message: str
) -> None:
    model = tmp_path / "broken.obj"
    model.write_text(content, encoding="utf-8")

    with pytest.raises(ObjParseError, match=message):
        parse_obj(model)


def test_empty_obj_is_rejected(tmp_path: Path) -> None:
    model = tmp_path / "empty.obj"
    model.write_text("# no geometry\n", encoding="utf-8")

    with pytest.raises(ObjParseError, match="no vertices"):
        parse_obj(model)


@pytest.mark.parametrize("content, message", [
    ("v 0 0 0\nf 1 1 1\n", "repeated vertices"),
    ("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 -3\n", "repeated vertices"),
    ("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3 1\n", "repeated vertices"),
    ("v 0 0 0\nv 0 0 0\nv 0 1 0\nf 1 2 3\n", "repeated vertices"),
    ("v 0 0 0\nv 1 1 1\nv 2 2 2\nf 1 2 3\n", "zero area"),
])
def test_degenerate_faces_are_rejected(tmp_path, content, message):
    path = tmp_path / "degenerate.obj"
    path.write_text(content)
    with pytest.raises(ObjParseError, match=message):
        parse_obj(path)


@pytest.mark.parametrize("height", ["1e200", "1e-200"])
def test_large_finite_coordinates_do_not_overflow_or_underflow_face_area(tmp_path, height):
    path = tmp_path / "large.obj"
    path.write_text(f"v 0 0 0\nv 1e200 0 0\nv 0 {height} 0\nf 1 2 3\n")
    assert parse_obj(path).triangles == 1


@pytest.mark.parametrize("vertices", [
    # Independent edges remain nonparallel even when their scales differ by 1e400.
    "v 0 0 0\nv 1e-200 0 0\nv 1e200 1 0\n",
    "v 0 0 0\nv 1e200 0 0\nv 0 1e200 1e200\n",
    "v 0 0 0\nv 1e-200 0 0\nv 0 1e-200 1e-200\n",
    "v -3 -3 -3\nv -1 -3 -3\nv -3 -1 -3\n",
    "v 1 2 3\nv 2 4 6\nv 2 2 4\n",
    # A representable departure from collinearity must not be rounded to zero.
    "v 0 0 0\nv 1 1 1\nv 2 2 2.0000000000000004\n",
    "v 0 0 0\nv 5e-324 0 0\nv 0 5e-324 0\n",
], ids=["mixed-scales", "large", "tiny", "negative", "oblique", "near-collinear", "subnormal"])
def test_noncollinear_triangles_are_not_zero_area(tmp_path, vertices):
    path = tmp_path / "triangle.obj"
    path.write_text(vertices + "f 1 2 3\n")
    stats = parse_obj(path)
    assert stats.faces == 1
    assert stats.triangles == 1


@pytest.mark.parametrize("vertices", [
    # The translated edges are (1, 2, 3) and twice that vector.
    "v 1 1 1\nv 2 3 4\nv 3 5 7\n",
    "v -1 -1 -1\nv -2 -3 -4\nv -3 -5 -7\n",
])
def test_translated_collinear_triangles_are_zero_area(tmp_path, vertices):
    path = tmp_path / "collinear.obj"
    path.write_text(vertices + "f 1 2 3\n")
    with pytest.raises(ObjParseError, match="zero area"):
        parse_obj(path)


@pytest.mark.parametrize("points", [
    [(0, 0, 0), (2, 0, 0), (1, .5, 0), (2, 2, 0), (0, 2, 0)],
    # The first fan triangle is collinear, but the second has nonzero area.
    [(0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 1, 0)],
    # Nonzero fan triangles may have cancelling oriented area vectors.
    [(0, 0, 1), (1, 1, -1), (1, -1, 1), (0, 0, -1), (-1, 1, 1), (-1, -1, -1)],
    # Self-intersection is outside this reader's validity checks.
    [(0, 0, 0), (1, 1, 0), (0, 1, 0), (1, 0, 0)],
    [(0, 0, 0), (3, 2, 0), (0, 2, 0), (2, 0, 0)],
], ids=["concave", "one-collinear-fan-triangle", "nonplanar-cancellation", "symmetric-bow-tie", "asymmetric-bow-tie"])
def test_polygons_with_noncollinear_geometry_keep_virtual_triangle_count(tmp_path, points):
    path = tmp_path / "polygon.obj"
    path.write_text(
        "".join("v " + " ".join(str(axis) for axis in point) + "\n" for point in points)
        + "f " + " ".join(str(index + 1) for index in range(len(points))) + "\n"
    )
    stats = parse_obj(path)
    assert stats.faces == 1
    assert stats.triangles == len(points) - 2


def test_polygon_with_all_collinear_fan_triangles_is_zero_area(tmp_path):
    path = tmp_path / "collinear-polygon.obj"
    path.write_text("v 1 1 1\nv 2 3 4\nv 3 5 7\nv 4 7 10\nf 1 2 3 4\n")
    with pytest.raises(ObjParseError, match="zero area"):
        parse_obj(path)
