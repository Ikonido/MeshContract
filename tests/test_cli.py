import json
from pathlib import Path

import pytest

from meshcontract import __version__
from meshcontract.cli import main


@pytest.mark.parametrize("duplicate", [False, True])
def test_invalid_geometry_or_duplicate_contract_returns_json_error(tmp_path, capsys, duplicate):
    model = tmp_path / "model.obj"
    model.write_text("v 0 0 0\nf 1 1 1\n")
    contract = tmp_path / "contract.yml"
    contract.write_text(
        "version: 1\ngeometry:\n  max_width_m: 1\n  max_width_m: 3\n"
        if duplicate else "version: 1\ngeometry: {}\n"
    )
    assert main(["check", str(model), "--contract", str(contract), "--format", "json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == ("invalid_contract" if duplicate else "invalid_input")


def test_cli_passes_example(capsys) -> None:
    example_dir = Path(__file__).parents[1] / "examples"

    result = main(
        [
            "check",
            str(example_dir / "example.obj"),
            "--contract",
            str(example_dir / ".meshcontract.yml"),
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert "Vertices: 8" in output
    assert "Faces: 6" in output
    assert "Triangles: 12" in output
    assert "PASS" in output


def test_cli_returns_nonzero_for_contract_violation(tmp_path: Path, capsys) -> None:
    model = tmp_path / "triangle.obj"
    model.write_text("v 0 0 0\nv 2 0 0\nv 0 2 0\nf 1 2 3\n", encoding="utf-8")
    contract = tmp_path / ".meshcontract.yml"
    contract.write_text("version: 1\ngeometry:\n  max_vertices: 2\n", encoding="utf-8")

    result = main(["check", str(model), "--contract", str(contract)])

    output = capsys.readouterr().out
    assert result == 1
    assert "FAIL" in output
    assert "max_vertices exceeded" in output


def test_cli_rejects_obj_without_faces(tmp_path: Path, capsys) -> None:
    model = tmp_path / "point_cloud.obj"
    model.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\n", encoding="utf-8")
    contract = tmp_path / ".meshcontract.yml"
    contract.write_text(
        "version: 1\ngeometry:\n  max_vertices: 10\n  max_triangles: 10\n",
        encoding="utf-8",
    )

    result = main(
        [
            "check",
            str(model),
            "--contract",
            str(contract),
            "--format",
            "json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 2
    assert captured.err == ""
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_input"
    assert "no faces found" in payload["error"]["message"]


def test_cli_reports_invalid_yaml_without_traceback(tmp_path: Path, capsys) -> None:
    contract = tmp_path / ".meshcontract.yml"
    contract.write_text("version: [\n", encoding="utf-8")
    model = Path(__file__).parents[1] / "examples" / "example.obj"

    result = main(["check", str(model), "--contract", str(contract)])

    error = capsys.readouterr().err
    assert result == 2
    assert "ERROR: invalid YAML" in error
    assert "Traceback" not in error


def test_cli_json_pass_reports_metrics_without_text_output(capsys) -> None:
    example_dir = Path(__file__).parents[1] / "examples"
    model = example_dir / "example.obj"

    result = main(
        [
            "check",
            str(model),
            "--contract",
            str(example_dir / ".meshcontract.yml"),
            "--format",
            "json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 0
    assert captured.err == ""
    assert payload == {
        "meshcontract_version": __version__,
        "status": "pass",
        "model": str(model),
        "metrics": {
            "vertices": 8,
            "faces": 6,
            "triangles": 12,
            "dimensions_m": {"width": 2.0, "length": 4.0, "height": 3.0},
        },
        "violations": [],
    }
    assert "Model:" not in captured.out
    assert "PASS" not in captured.out


def test_cli_json_fail_has_structured_violations(tmp_path: Path, capsys) -> None:
    model = tmp_path / "triangle.obj"
    model.write_text("v 0 0 0\nv 2 0 0\nv 0 2 0\nf 1 2 3\n", encoding="utf-8")
    contract = tmp_path / ".meshcontract.yml"
    contract.write_text(
        "version: 1\ngeometry:\n  max_vertices: 2\n  max_width_m: 1\n",
        encoding="utf-8",
    )

    result = main(
        ["check", str(model), "--contract", str(contract), "--format", "json"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 1
    assert captured.err == ""
    assert payload["status"] == "fail"
    assert payload["metrics"]["vertices"] == 3
    assert payload["metrics"]["faces"] == 1
    assert payload["metrics"]["triangles"] == 1
    assert payload["violations"] == [
        {
            "code": "max_vertices_exceeded",
            "rule": "max_vertices",
            "message": "max_vertices exceeded: 3 > 2",
            "actual": 3,
            "limit": 2,
        },
        {
            "code": "max_width_m_exceeded",
            "rule": "max_width_m",
            "message": "max_width_m exceeded: 2.000 m > 1.000 m",
            "actual": 2.0,
            "limit": 1.0,
        },
    ]
    assert "FAIL" not in captured.out


def test_cli_json_invalid_contract_is_machine_readable(tmp_path: Path, capsys) -> None:
    contract = tmp_path / ".meshcontract.yml"
    contract.write_text("version: [\n", encoding="utf-8")
    model = Path(__file__).parents[1] / "examples" / "example.obj"

    result = main(
        ["check", str(model), "--contract", str(contract), "--format", "json"]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 2
    assert captured.err == ""
    assert payload["status"] == "error"
    assert payload["metrics"] is None
    assert payload["violations"] == []
    assert payload["error"]["code"] == "invalid_contract"


def test_cli_json_reports_oversized_dimension_without_traceback(
    tmp_path: Path, capsys
) -> None:
    contract = tmp_path / ".meshcontract.yml"
    huge_integer = "9" * 400
    contract.write_text(
        f"version: 1\ngeometry:\n  max_width_m: {huge_integer}\n",
        encoding="utf-8",
    )
    model = Path(__file__).parents[1] / "examples" / "example.obj"

    result = main(
        [
            "check",
            str(model),
            "--contract",
            str(contract),
            "--format",
            "json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert result == 2
    assert captured.err == ""
    assert payload["status"] == "error"
    assert payload["metrics"] is None
    assert payload["error"]["code"] == "invalid_contract"
