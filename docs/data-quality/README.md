# ASM manifest data quality

The checked-in ASM manifests are a **versioned research and integration
dataset**, not a live price/SLA directory. Schema validity does not prove that a
provider claim is current.

Run the deterministic offline audit:

```bash
python3 tools/audit_manifest_data.py --as-of 2026-08-16 \
  --output docs/data-quality/manifest-audit-2026-08-16.json
```

Optionally probe provenance URLs (network results vary by location and bot
protection):

```bash
python3 tools/audit_manifest_data.py --as-of 2026-08-16 --check-urls \
  --output /tmp/asm-manifest-audit.json
```

## Freshness policy

Freshness is calculated from `provenance.last_verified_at`:

| Status | Verification age | Selection behavior |
|---|---:|---|
| `fresh` | 0–30 days | May be used, subject to its verification status. |
| `stale` | 31–90 days | Exclude from current-fact claims until reviewed. |
| `expired` | More than 90 days | Fixture and benchmark use only until re-verified. |
| `unknown` / `invalid` | No usable timestamp | Do not select without an explicit override. |

This is separate from a manifest's `ttl`. `ttl` controls how long a client may
cache a fetched live manifest; it is not evidence that a checked-in claim has
recently been verified. Verification status and freshness are also separate:
old manual verification still expires.

## URL interpretation

- `reachable`: HTTP 2xx/3xx;
- `access_restricted`: HTTP 401/403/407/418/429 — bot protection,
  authentication, or throttling; **not a dead-link finding**;
- `not_found`: only HTTP 404/410;
- `timeout`, `network_error`, `server_error`: inconclusive and should be retried;
- `invalid_or_tls_error`: URL or TLS needs manual review.

Source reachability does not verify the claims on the page. A refresh is only
complete when the relevant facts have been compared with the cited source and
the provenance notes document the scope.

## 2026-08-16 baseline

- `manifests/`: 75 entries; all 75 expired; 70 self-reported and 5 manually
  verified. Keep these as fixtures/benchmark snapshots until refreshed.
- `library/`: 30 entries; all 30 stale; 20 self-reported and 10 manually
  verified. Do not present these as current facts without review.
- All 105 entries pass ASM v0.3 schema and include required provenance fields.
  That is structural completeness, not truth verification.
- The 105 entries cite 99 unique source URLs. From this machine on 2026-08-16,
  95 returned 2xx/3xx, two were access-restricted (OpenAI 403 and DeepSeek
  401), one returned 405, and the DashScope API root returned 404. The last
  four require source review; they are not evidence that the providers are
  unavailable.

The generated baseline report preserves per-entry ages and issues:
[`manifest-audit-2026-08-16.json`](manifest-audit-2026-08-16.json).
