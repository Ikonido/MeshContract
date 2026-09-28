from meshcontract.contract import Contract
from meshcontract.obj import Dimensions, MeshStats
from meshcontract.validation import validate_mesh


def test_contract_passes_at_limits() -> None:
    stats = MeshStats(
        vertices=8,
        faces=6,
        triangles=12,
        dimensions=Dimensions(width_m=2, length_m=4, height_m=3),
        ngon_faces=0,
    )
    contract = Contract(
        version=1,
        max_triangles=12,
        max_vertices=8,
        max_width_m=2,
        max_height_m=3,
        max_length_m=4,
        allow_ngons=False,
    )

    assert validate_mesh(stats, contract) == []


def test_all_violations_are_returned() -> None:
    stats = MeshStats(
        vertices=9,
        faces=1,
        triangles=5,
        dimensions=Dimensions(width_m=2.5, length_m=4, height_m=3.5),
        ngon_faces=1,
    )
    contract = Contract(
        version=1,
        max_triangles=4,
        max_vertices=8,
        max_width_m=2,
        max_height_m=3,
        max_length_m=4,
        allow_ngons=False,
    )

    violations = validate_mesh(stats, contract)

    assert len(violations) == 5
    assert any("max_triangles" in violation for violation in violations)
    assert any("max_vertices" in violation for violation in violations)
    assert any("max_width_m" in violation for violation in violations)
    assert any("max_height_m" in violation for violation in violations)
    assert any("allow_ngons" in violation for violation in violations)
