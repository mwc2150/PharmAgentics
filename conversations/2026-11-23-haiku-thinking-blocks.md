# 2026-11-23 Briefing agent on Haiku: thinking blocks refused on newer accounts

Sienna, with Claude Opus. Committed to `main`.

## What happened

Recording the demo locally with Sienna's Anthropic key (`PHARMAGENTICS_AGENT_MODEL=anthropic:claude-haiku-5-5`, built-in worker), the Briefing agent team failed in two of three runs:

```
Magentic Orchestrator: Progress ledger creation failed, triggering reset: Invalid Anthropic request: Error code: 400 -
messages.5.content.0: Invalid `signature` in `thinking` block. The block is bound to a different conversation. Remove the
block, or set `thinking.block_binding.prefix_mismatch_behavior` to "drop_block". That setting requires the
`thinking-binding-controls-2026-08-01` value in the `anthropic-beta` header.
Magentic Orchestrator: Max reset count reached
```

Claude Haiku 5.5 thinks by default, and its thinking blocks are bound to the conversation that produced them. Magentic's orchestrator rewrites its own message history when it rebuilds the progress ledger, so a replayed thinking block no longer matches. Anthropic refuses this on accounts held to the history-editing check (newer accounts); the team key may not be held to it yet, which would explain why Michael's runs pass.

## Change

`src/pharmagentics/llm.py` `chat_options`: when `PHARMAGENTICS_ANTHROPIC_THINKING` is `off` (or `disabled`, `0`), Claude requests carry `thinking: {type: disabled}`, so no thinking blocks exist to be refused. Unset, the request is exactly as before. Every Briefing agent (manager, specialists, writer, scope reader) and the Forecast model calls take their options from `chat_options`.

With the switch on: three Briefing agent runs and the full demo recording finished with no errors (about 70 to 95 s per brief after plan approval). `tests/test_llm_options.py` covers the switch.

## Open (Michael)

- Whether the hosted app and `compose.yaml` should set the switch, or keep thinking and send the beta header `thinking-binding-controls-2026-08-01` with `thinking.block_binding.prefix_mismatch_behavior: "drop_block"` (Agent Framework would need to pass both through).
- The golden set has not been run with the switch on; run `eval run --system briefing_agent --model anthropic:claude-haiku-5-5` with and without it and gate before changing any default.
