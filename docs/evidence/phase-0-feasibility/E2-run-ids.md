# E-2 Run IDs and SHAs

状态：`RECORDED — AUTHORITATIVE GITHUB EVIDENCE`

| Evidence | Exact value |
|---|---|
| Repository | `cmylittlej-ux/ai-control-center-e2-sandbox` |
| Workflow | `.github/workflows/e2-authoritative.yml` |
| Required check | `authoritative-ci` |
| Ruleset | `E2 Main Protection` |
| PR | `#1 — E2 Worker Authoritative CI Probe` |
| Positive matrix | `20/20 PASS` before intentional failure probe |
| Latest good head before failure | `e796615093ab139f1c832b80f92f4abb0a1cca16` |
| Example/latest successful Run ID | `33856286499` |
| Intentional failure commit | `ef1fe9407acc1514fa484e2d14fea4cf19f6523c` |
| Authoritative failing Run ID | `33856752481` |
| Main SHA after blocked merge | `99c99b53dc0c05f11e762776690b9304ae9c0622` |

The 20-run positive matrix is recorded by count; the exact run list remains in the authoritative GitHub repository history. No local run is represented as an authoritative GitHub Run ID.
