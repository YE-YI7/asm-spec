# Release Notes: v0.3.1

ASM v0.3.1 turns the paper artifact into an adoption artifact for MCP publishers and aggregators.

## Included

- ASM v0.3 JSON Schema.
- 75 source-linked manifests across 47 taxonomies.
- MCP Registry `server.json` examples with ASM embedded under `_meta.io.modelcontextprotocol.registry/publisher-provided.asm`.
- `asm-mcp-validate` CLI for validating and extracting ASM metadata from `server.json`.
- `asm score` CLI demo for natural-language service selection.
- Reproducibility instructions in `ARTIFACT.md`.
- Paper draft in `paper/asm-paper-draft.md`.

## Example

```bash
pip install -e .
asm score "cheap reliable TTS under 1s"
asm-mcp-validate examples/mcp-server-json/remote-with-asm.server.json
```

## Citation

Until a Zenodo DOI or arXiv identifier is available, cite the GitHub release tag and commit SHA:

```text
Guo, Y. Agent Service Manifest (ASM) v0.3.1. GitHub release, 2026.
https://github.com/YE-YI7/asm-spec/releases/tag/v0.3.1
Tag target: see the `v0.3.1` Git tag for the exact commit SHA.
```

## Caveat

ASM does not prove that any quality metric is universally correct. It makes declared value metadata computable and auditable; registries and selectors must respect metric provenance and benchmark compatibility.
