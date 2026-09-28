# MeshContract

**Requirements-as-code for 3D assets. Think ESLint or a test suite, but for 3D assets.**

MeshContract reads technical limits from a YAML contract and checks a model from the command line. The first release supports Wavefront OBJ geometry checks.

## Quick start

Python 3.11 or newer is required.

```bash
pip install -e .
meshcontract check examples/example.obj --contract examples/.meshcontract.yml
```

The example should pass and report 8 vertices, 6 faces, 12 triangles, and dimensions of 2 × 4 × 3 m.

Run the unit tests with:

```bash
pip install -e '.[dev]'
pytest
```

GitHub Actions runs the full test suite on Python 3.11 and 3.12 for every push and pull request.

## Contract

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

All limits are optional. A face with `n` vertices contributes `n - 2` to the triangle count; this is calculated without changing the OBJ file. An n-gon means a face with more than four vertices, so quads are allowed even when `allow_ngons` is false.

OBJ does not specify a universal unit or axis convention. MeshContract treats coordinate values as meters and maps X to width, Y to length, and Z to height. Export models using that convention, or transform them before checking.

## Current scope

MeshContract reports vertex and face counts, virtual triangle count, and axis-aligned dimensions. It checks `max_triangles`, `max_vertices`, `max_width_m`, `max_height_m`, `max_length_m`, and `allow_ngons`. Invalid OBJ geometry and invalid contract YAML produce a readable error and a non-zero exit code.

This MVP does not validate UVs, textures, materials, normals, naming, or collision meshes. Additional file formats and validators can be added independently of the core contract checks.

## Next steps for v0.2

- Add JSON output for CI and other tools.
- Add a glTF/GLB reader behind the same geometry metrics interface.
- Add UV and texture checks with focused contract sections.
- Add Unity/Unreal contract presets.
- Explore semantic comparisons between two asset versions.

MeshContract is released under the MIT License; see [LICENSE](LICENSE).
