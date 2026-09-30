# Changelog

## Unreleased

- Reject duplicate contract keys and OBJ faces with repeated vertices or zero area.
- Run the full test suite on the release tag before building PyPI distributions.

## v0.2.1

- Reject OBJ files that contain vertices but no faces.
- Report oversized dimension limits as a normal `ContractError` and structured CLI error instead of an uncaught `OverflowError`.
- Add regression tests for both fixes.
- No new file formats or contract rules.

## v0.2.0

- JSON output
- Structured violations
- GitHub Actions example
- Packaging metadata
- Compatibility with v0.1 contracts

## v0.1.0

- Initial OBJ validation MVP
