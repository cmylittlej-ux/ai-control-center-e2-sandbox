# Codex Usage Capability Probe

状态：PASS FOR PHASE 0 — LIVE FIELDS OBSERVED

Probe 时间：2026-09-04（Australia/Melbourne）

## Verified runtime

- Dedicated Worker identity: macOS Standard User aicc-worker.
- Codex CLI/App Server: 0.153.2; App Server operational.
- A real App Server Turn completed successfully on a disposable fixture.
- Only the expected repository file changed and the fixture test passed.

## Live structured evidence

The real Turn emitted thread/tokenUsage/updated. The following fields were available:

| Field | Available | Source | Observation |
|---|---|---|---|
| input tokens | yes | thread/tokenUsage/updated → tokenUsage.last/total.inputTokens | live |
| cached input tokens | yes | ...cachedInputTokens | live |
| output tokens | yes | ...outputTokens | live |
| reasoning output tokens | yes | ...reasoningOutputTokens | live |
| total tokens | yes | ...totalTokens | live |
| model context window | yes | ThreadTokenUsage.modelContextWindow | observed 258400 |
| Account rate limits | yes | AccountRateLimitsUpdated | primary and secondary windows |
| plan type | yes | account evidence | Plus |

The evidence does not claim a per-turn resolved model ID/version that was not supplied in the verified result. Phase 1 must preserve configured/resolved model metadata when present and pin the exact executable/schema artifact before implementation.

## Billing mode and semantics

This probe is ChatGPT subscription/runtime usage evidence. Do not classify it as actual API billing cost.

- api_billed: provider-confirmed usage × versioned rate card may be labeled API actual cost.
- chatgpt_subscription: show Token plus an explicitly labeled API-equivalent estimate; it is not actual billing.
- unknown: show Usage/Cost unavailable or uncertain; never infer cost from API prices.

The architecture’s billing semantics are unchanged.

## Schema provenance

The local App Server schema bundle remains at docs/evidence/phase-0-feasibility/app-server-schema/. Official OpenAI App Server documentation states that generated schema output is specific to the Codex version being executed; Phase 1 must capture the 0.153.2 schema/build pin before integration.
