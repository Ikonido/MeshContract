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
