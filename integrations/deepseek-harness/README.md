# ASM for DeepSeek Harness

This package adds two native DeepSeek Harness tools: `asm_list_services` shows
what the configured catalog actually covers, and `asm_select` chooses within
one explicit taxonomy and returns the decision with a Selection Receipt.

It is deliberately narrow:

- it selects; it does not invoke the selected service;
- an `approval_required` result is not user authorization;
- Selection Receipts are unsigned evidence, not cryptographic attestation;
- it does not claim that the configured ASM catalog covers every Harness tool;
- it does not send task text to a remote endpoint unless you configure one.

## Run the selector locally

From the ASM repository root:

```bash
python asm_select_api.py
```

The plugin defaults to `http://127.0.0.1:8787`. To opt into another endpoint,
set `ASM_SELECTOR_URL` before starting DeepSeek Harness.

## Install a local checkout

Build this package, then add it to the target Harness profile:

```bash
cd integrations/deepseek-harness
npm install
npm run check
dsh plugin --profile web add .
dsh --profile web
```

Restart the profile after adding, removing, or updating the bundle. The package
contributes its `cordis.patch.yml` automatically.

## What the Agent sees

The selection tool accepts the same constraints as `POST /select`: task, taxonomy,
runtime reach, user platform, required functions, approval-triggering side
effects, and whether setup must be agent-completable. It always requests a
Selection Receipt.

`taxonomy` is required by the Harness adapter. The current ASM library selector
does not infer taxonomy from natural-language task text, so allowing an
unbounded cross-category call would create a plausible-looking but invalid
choice. Use `asm_list_services` first when the taxonomy is unknown.

Use it when several catalogued services can satisfy a consequential task. Do
not use it as a generic web search or as evidence that an uncatalogued tool is
ineligible.

## Developer preview compatibility

DeepSeek Harness is currently a developer preview. This package targets:

- `@deepseek-ai/dsh` 0.1.1-rc.2;
- `@deepseek-ai/dsh-tools` 0.1.1-rc.2;
- `@deepseek-ai/cordis` 4.0.1.

The boundary is intentionally only `ctx.tools.register(defineTool(...))` plus
the documented bundle patch, so future Harness changes are isolated here. The
Cordis and tool-runtime peer packages are supplied by the Harness base bundle;
they remain development dependencies here for type checking and tests.

## M3 contract-seam fixture

The synthetic conformance fixture at
`examples/interop/deepseek-harness-selection-boundary/` separately proves the
proposed DSH Bundle-identity versus mutable Selection-Facts-digest boundary.
It is one M3 contract seam, not a planner, installer, evaluator, or adoption
claim.
