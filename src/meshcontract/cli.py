"""Command-line interface for MeshContract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .contract import ContractError, load_contract
from .models import MeshStats, ValidationResult
from .obj import ObjParseError, parse_obj
from .validation import evaluate_mesh


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
    check.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    return parser


def _metrics_payload(stats: MeshStats) -> dict[str, object]:
    """Convert shared geometry metrics to the stable JSON schema."""
    return {
        "vertices": stats.vertices,
        "faces": stats.faces,
        "triangles": stats.triangles,
        "dimensions_m": {
            "width": stats.dimensions.width_m,
            "length": stats.dimensions.length_m,
            "height": stats.dimensions.height_m,
        },
    }


def _json_payload(model_path: Path, result: ValidationResult) -> dict[str, object]:
    """Build the stable JSON document from the backend-independent result."""
    return {
        "meshcontract_version": __version__,
        "status": result.status,
        "model": str(model_path),
        "metrics": _metrics_payload(result.metrics),
        "violations": [
            {
                "code": violation.code,
                "rule": violation.rule,
                "message": violation.message,
                "actual": violation.actual,
                "limit": violation.limit,
            }
            for violation in result.violations
        ],
    }


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _report_error(
    model_path: Path,
    output_format: str,
    code: str,
    message: str,
) -> int:
    if output_format == "json":
        _print_json(
            {
                "meshcontract_version": __version__,
                "status": "error",
                "model": str(model_path),
                "metrics": None,
                "violations": [],
                "error": {"code": code, "message": message},
            }
        )
    else:
        print(f"ERROR: {message}", file=sys.stderr)
    return 2


def _print_text(model_path: Path, result: ValidationResult) -> None:
    stats = result.metrics
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

    if result.violations:
        print(f"FAIL — {len(result.violations)} contract violation(s)")
        for violation in result.violations:
            print(f"  - {violation.message}")
        return

    print("PASS — contract satisfied")


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    model_path: Path = args.model
    output_format: str = args.format
    if model_path.suffix.lower() != ".obj":
        return _report_error(
            model_path,
            output_format,
            "unsupported_format",
            f"unsupported model format {model_path.suffix or '(no extension)'!r}; "
            "this release supports Wavefront OBJ only",
        )

    try:
        contract = load_contract(args.contract)
        stats = parse_obj(model_path)
    except ContractError as exc:
        return _report_error(model_path, output_format, "invalid_contract", str(exc))
    except ObjParseError as exc:
        return _report_error(model_path, output_format, "invalid_input", str(exc))

    result = evaluate_mesh(stats, contract)
    if output_format == "json":
        _print_json(_json_payload(model_path, result))
    else:
        _print_text(model_path, result)

    return 1 if result.violations else 0
