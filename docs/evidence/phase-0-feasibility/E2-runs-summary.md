# E-2 Verification Runs Summary

状态：`PASS — AUTHORITATIVE GITHUB-HOSTED VERIFICATION`

## Authoritative target

- Disposable repository: `cmylittlej-ux/ai-control-center-e2-sandbox`
- Workflow: `.github/workflows/e2-authoritative.yml`
- Required check: `authoritative-ci`
- Ruleset: `E2 Main Protection`
- PR: `#1 — E2 Worker Authoritative CI Probe`

## Positive reliability evidence

- 20 authoritative GitHub-hosted `pull_request` workflow runs completed successfully before the intentional failure probe.
- Success rate: `20/20 PASS`.
- Latest successful head before failure: `e796615093ab139f1c832b80f92f4abb0a1cca16`.
- Example/latest successful Run ID: `33856286499`.

## Negative gate evidence

- Intentional failure commit: `ef1fe9407acc1514fa484e2d14fea4cf19f6523c`.
- Authoritative GitHub-hosted Run ID: `33856752481`.
- Result: `failure`.
- Worker merge attempt: HTTP `405`; `Repository rule violations found Required status check "authoritative-ci" is failing.`
- PR remained open and `merged=false`.
- Main SHA remained unchanged: `99c99b53dc0c05f11e762776690b9304ae9c0622`.

## E-2 conclusion

The GitHub-hosted ephemeral authoritative check is reliable for the required probe, and the failing required check blocks merge. The authoritative remote evidence, not the earlier local baseline, is the basis for E-2 PASS.
