"""Command-line interface for MeshContract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .contract import ContractError, load_contract
from .obj import ObjParseError, parse_obj
from .validation import validate_mesh


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="meshcontract",
        description="Check a 3D asset against a versioned YAML contract.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="check a Wavefront OBJ model")
    check.add_argument("model", type=Path, help="path to a Wavefront OBJ file")
    check.add_argument(
        "--contract",
        type=Path,
        default=Path(".meshcontract.yml"),
        help="contract YAML file (default: .meshcontract.yml)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    model_path: Path = args.model
    if model_path.suffix.lower() != ".obj":
        print(
            f"ERROR: unsupported model format {model_path.suffix or '(no extension)'!r}; "
            "this release supports Wavefront OBJ only",
            file=sys.stderr,
        )
        return 2

    try:
        contract = load_contract(args.contract)
        stats = parse_obj(model_path)
    except (ContractError, ObjParseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Model: {model_path}")
    print(f"Vertices: {stats.vertices}")
    print(f"Faces: {stats.faces}")
    print(f"Triangles: {stats.triangles}")
    print(
        "Dimensions: "
        f"width={stats.dimensions.width_m:.3f} m, "
        f"length={stats.dimensions.length_m:.3f} m, "
        f"height={stats.dimensions.height_m:.3f} m"
    )

    violations = validate_mesh(stats, contract)
    if violations:
        print(f"FAIL — {len(violations)} contract violation(s)")
        for violation in violations:
            print(f"  - {violation}")
        return 1

    print("PASS — contract satisfied")
    return 0
