# E-1 Environment Probe

状态：`PASS — HUMAN BOOTSTRAP VERIFIED`

## Dedicated Worker environment

- Dedicated macOS Standard User: `aicc-worker`
- `aicc-worker` is not a member of the admin group.
- Worker home: `/Users/aicc-worker`
- AICC root mode: `700`
- Main-user SSH access: denied.
- Main-user Keychains access: denied.
- Main-user Chrome profile access: denied.
- Worker had no pre-existing `~/.ssh`, `~/.npmrc`, API/token environment variables.

## Boundary checks

- Worker write outside the repository: denied.
- Main-user directory write: denied.
- Main-user `.ssh` read: denied.
- Main-user Keychains read: denied.
- Shell-tool outbound network: denied during probe.
- No protected secret, Keychain, browser-profile or token value was copied into evidence.

## Codex runtime

- Codex CLI: `0.153.2`
- Codex App Server: available and operational.
- A real App Server Turn completed successfully.
- Disposable fixture changed only the expected repository file.
- Fixture test passed.

## Live structured usage

- `thread/tokenUsage/updated` was received from the real App Server Turn.
- Available fields: `inputTokens`, `cachedInputTokens`, `outputTokens`, `reasoningOutputTokens`, `totalTokens`, `modelContextWindow`.
- Observed `modelContextWindow`: `258400`.
- `AccountRateLimitsUpdated` was observed.
- `plan_type`: `Plus`.
- Primary and secondary rate-limit windows were available.

## E-1 conclusion

The verified dedicated identity, deny-boundary checks, real App Server Turn, fixture modification/test result, and live structured usage evidence satisfy the frozen E-1 acceptance criteria. ChatGPT subscription usage is not API billing cost; the frozen billing semantics remain unchanged.
