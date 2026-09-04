# E-1 Policy Results

状态：`PASS`

| Control | Result | Evidence |
|---|---|---|
| Dedicated Worker identity | PASS | macOS Standard User `aicc-worker`; not in admin group |
| Worker home and root boundary | PASS | `/Users/aicc-worker`; AICC root mode `700` |
| Worker pre-existing secret/config state | PASS | no pre-existing `~/.ssh`, `~/.npmrc`, API/token environment variables |
| Main-user SSH access | PASS | denied |
| Main-user Keychains access | PASS | denied |
| Main-user Chrome profile access | PASS | denied |
| Worker write outside repository | PASS | denied |
| Main-user directory write | PASS | denied |
| Main-user `.ssh` read | PASS | denied |
| Main-user Keychains read | PASS | denied |
| Shell-tool outbound network | PASS | denied during probe |
| Codex CLI/App Server | PASS | CLI `0.153.2`; App Server available and operational |
| Real App Server coding Turn | PASS | completed successfully; only expected fixture file changed |
| Fixture test | PASS | completed successfully |
| Runtime structured events | PASS | `thread/tokenUsage/updated` received from real Turn |
| Usage/token fields | PASS | input, cached input, output, reasoning output, total, context window available; context window observed `258400` |
| Account/rate-limit evidence | PASS | `AccountRateLimitsUpdated`; `plan_type: Plus`; primary and secondary windows available |

No secret values, Keychain contents, browser profiles or raw token values were read or recorded.
