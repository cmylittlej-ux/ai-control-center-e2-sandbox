# E-2 Permissions Check

状态：`PASS`

## Credential

Temporary fine-grained PAT restricted only to `cmylittlej-ux/ai-control-center-e2-sandbox`.

Worker permissions:

- Contents: Read/Write
- Pull Requests: Read/Write
- Metadata: Read
- no Administration
- no Workflows write
- no Actions write
- no Secrets/Environment administration

## Ruleset

`E2 Main Protection` was active on the default branch with pull request required, required status check `authoritative-ci`, up-to-date branch requirement, deletion blocked, non-fast-forward/force push blocked, and no bypass.

## Permission attack results

| Attempt | Result |
|---|---|
| Worker task branch push | PASS / allowed |
| PR creation | PASS / allowed |
| Direct main push | denied |
| Force push main | denied |
| Ruleset create/modify attempt | HTTP 403 |
| Actions Run deletion attempt | HTTP 403 |
| Workflow modification push | rejected with: `refusing to allow a Personal Access Token to create or update workflow .github/workflows/e2-authoritative.yml without workflow scope` |

The checks prove the Worker can submit work to the disposable repository while lacking the authority to change the protection policy, delete Actions evidence, force-update main, or modify the authoritative workflow.
