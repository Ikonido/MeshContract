from pathlib import Path

import pytest

from meshcontract.contract import ContractError, load_contract


def test_loads_contract(tmp_path: Path) -> None:
    contract_path = tmp_path / ".meshcontract.yml"
    contract_path.write_text(
        "version: 1\ngeometry:\n  max_triangles: 12\n  max_width_m: 2.5\n  allow_ngons: false\n",
        encoding="utf-8",
    )

    contract = load_contract(contract_path)

    assert contract.version == 1
    assert contract.max_triangles == 12
    assert contract.max_vertices is None
    assert contract.max_width_m == 2.5
    assert contract.allow_ngons is False


@pytest.mark.parametrize(
    "content, message",
    [
        ("version: [\n", "invalid YAML"),
        ("version: 2\ngeometry: {}\n", "version must be the integer 1"),
        ("version: 1\n", "must contain a geometry mapping"),
        ("version: 1\ngeometry:\n  max_vertices: -1\n", "non-negative integer"),
        ("version: 1\ngeometry:\n  max_vertices: 1.5\n", "non-negative integer"),
        ("version: 1\ngeometry:\n  allow_ngons: 'no'\n", "must be true or false"),
        ("version: 1\ngeometry:\n  max_triangles: 1\n  typo: true\n", "unknown geometry key"),
        ("version: 1\ngeometry: []\n", "geometry must be a YAML mapping"),
    ],
)
def test_invalid_contracts_are_reported(
    tmp_path: Path, content: str, message: str
) -> None:
    contract_path = tmp_path / "bad.yml"
    contract_path.write_text(content, encoding="utf-8")

    with pytest.raises(ContractError, match=message):
        load_contract(contract_path)
