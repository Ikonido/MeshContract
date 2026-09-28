from pathlib import Path

from meshcontract.cli import main


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


def test_cli_reports_invalid_yaml_without_traceback(tmp_path: Path, capsys) -> None:
    contract = tmp_path / ".meshcontract.yml"
    contract.write_text("version: [\n", encoding="utf-8")
    model = Path(__file__).parents[1] / "examples" / "example.obj"

    result = main(["check", str(model), "--contract", str(contract)])

    error = capsys.readouterr().err
    assert result == 2
    assert "ERROR: invalid YAML" in error
    assert "Traceback" not in error
