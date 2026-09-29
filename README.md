# MeshContract

**Requirements-as-code for 3D assets. Think ESLint or a test suite, but for 3D assets.**

Describe geometry limits in YAML and check Wavefront OBJ files from the command line. MeshContract returns a CI-friendly exit code and can emit text or JSON.

## Installation

Python 3.11 or newer is required. Install the released package from [PyPI](https://pypi.org/project/meshcontract/):

```bash
pip install meshcontract
```

To install the current development source from GitHub instead:

```bash
python -m pip install "git+https://github.com/Ikonido/MeshContract.git@main"
```

For local development, clone the repository and install it in editable mode:

```bash
git clone https://github.com/Ikonido/MeshContract.git
cd MeshContract
python -m pip install -e '.[dev]'
```

## Quick start

```bash
meshcontract check examples/example.obj --contract examples/.meshcontract.yml
```

Text is the default output and remains suitable for interactive use:

```text
Model: examples/example.obj
Vertices: 8
Faces: 6
Triangles: 12
Dimensions: width=2.000 m, length=4.000 m, height=3.000 m
PASS — contract satisfied
```

For scripts and CI, request stable JSON output:

```bash
meshcontract check examples/example.obj --contract examples/.meshcontract.yml --format json
```

```json
{
  "meshcontract_version": "0.2.1",
  "status": "pass",
  "model": "examples/example.obj",
  "metrics": {
    "vertices": 8,
    "faces": 6,
    "triangles": 12,
    "dimensions_m": {
      "width": 2.0,
      "length": 4.0,
      "height": 3.0
    }
  },
  "violations": []
}
```

## YAML contract

```yaml
version: 1

geometry:
  max_triangles: 30000
  max_vertices: 25000
  max_width_m: 17
  max_height_m: 20
  max_length_m: 70
  allow_ngons: false
```

All limits are optional. A face with `n` vertices contributes `n - 2` to the virtual triangle count; the OBJ file is not changed. An n-gon means a face with more than four vertices, so quads are allowed when `allow_ngons` is false.

OBJ does not define a universal unit or axis convention. MeshContract treats coordinate values as meters and maps X to width, Y to length, and Z to height. Export models using that convention, or transform them before checking.

## CI / GitHub Actions

Exit codes are stable for CI: `0` means the contract passed, `1` means one or more contract violations, and `2` means invalid input, an invalid contract, or an unsupported model format. A non-zero code fails a GitHub Actions step by default.

The repository includes a copyable [GitHub Actions workflow example](examples/github-actions/meshcontract.yml). Copy it to `.github/workflows/` in your asset repository and update the OBJ and contract paths in its final step. It installs the released package from PyPI, pinned to `meshcontract==0.2.1` for reproducible builds.

The project test workflow runs the full pytest suite on Python 3.11 and 3.12 for every push and pull request.

## Current scope

The v0.2 CI foundation checks Wavefront OBJ vertex and face counts, virtual triangle count, axis-aligned dimensions, and n-gons. JSON contract violations include a stable code, rule, message, actual value, and limit. Invalid input produces a JSON error object when `--format json` is selected.

The default text format and v0.1 YAML contract remain supported. MeshContract does not currently validate UVs, textures, materials, normals, naming, or collision meshes.

## Roadmap

- Add additional asset backends behind the shared geometry model.
- Explore UV, texture, material, naming, and collision contract sections.
- Consider engine presets, a custom GitHub Action, and semantic asset diffs.

MeshContract is released under the MIT License; see [LICENSE](LICENSE).
