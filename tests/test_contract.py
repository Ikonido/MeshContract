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


def test_oversized_dimension_is_reported_as_contract_error(tmp_path: Path) -> None:
    contract_path = tmp_path / "oversized.yml"
    huge_integer = "9" * 400
    contract_path.write_text(
        f"version: 1\ngeometry:\n  max_width_m: {huge_integer}\n",
        encoding="utf-8",
    )

    with pytest.raises(ContractError, match="finite non-negative number"):
        load_contract(contract_path)


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


@pytest.mark.parametrize("content", [
    "version: 1\nversion: 1\ngeometry: {}\n",
    "version: 1\ngeometry:\n  max_width_m: 1\n  max_width_m: 3\n",
    "version: 1\ngeometry: {}\ngeometry: {}\n",
])
def test_duplicate_contract_keys_are_rejected(tmp_path, content):
    path = tmp_path / "contract.yml"
    path.write_text(content)
    with pytest.raises(ContractError, match="duplicate key"):
        load_contract(path)


def test_yaml_merge_can_override_an_inherited_limit(tmp_path):
    path = tmp_path / "contract.yml"
    path.write_text(
        "version: 1\ngeometry:\n  <<: &defaults {max_width_m: 1}\n  max_width_m: 2\n"
    )
    assert load_contract(path).max_width_m == 2


@pytest.mark.parametrize("geometry", [
    "  <<: {max_width_m: 1, max_width_m: 2}\n",
    "  <<: [&d {max_width_m: 1, max_width_m: 2}, *d]\n",
    "  <<: {<<: {max_width_m: 1, max_width_m: 2}}\n",
    "  <<: {max_width_m: 1}\n  <<: {max_width_m: 2}\n",
    "  <<: {<<: {max_width_m: 1}, <<: {max_width_m: 2}}\n",
])
def test_raw_merge_source_duplicates_are_rejected(tmp_path, geometry):
    path = tmp_path / "duplicate-merge.yml"
    path.write_text("version: 1\ngeometry:\n" + geometry)
    with pytest.raises(ContractError, match="duplicate key"):
        load_contract(path)


def test_merge_sequence_preserves_first_source_priority_and_explicit_override(tmp_path):
    path = tmp_path / "merge-sequence.yml"
    path.write_text(
        "version: 1\ngeometry:\n"
        "  <<: [&first {max_width_m: 1, max_height_m: 4},\n"
        "       {max_width_m: 2, max_length_m: 5}, *first]\n"
        "  max_height_m: 3\n"
    )
    contract = load_contract(path)
    assert contract.max_width_m == 1
    assert contract.max_height_m == 3
    assert contract.max_length_m == 5


def test_scalar_anchors_and_aliases_preserve_safe_loader_values(tmp_path):
    path = tmp_path / "aliases.yml"
    path.write_text("version: 1\ngeometry:\n  max_width_m: &limit 2\n  max_height_m: *limit\n")
    contract = load_contract(path)
    assert contract.max_width_m == contract.max_height_m == 2


@pytest.mark.parametrize("geometry, message", [
    ("  ? [a, b]\n  : 1\n", "hashable"),
    ("  max_width_m: !!python/object:builtins.object {}\n", "constructor"),
    # A recursive alias is legal YAML; the contract's field type is invalid.
    ("  max_width_m: &recursive [*recursive]\n", "finite non-negative number"),
])
def test_yaml_errors_and_invalid_alias_values_surface_as_contract_errors(tmp_path, geometry, message):
    path = tmp_path / "invalid.yml"
    path.write_text("version: 1\ngeometry:\n" + geometry)
    with pytest.raises(ContractError, match=message):
        load_contract(path)
