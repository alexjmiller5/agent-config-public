---
name: later
description: Follow-up prompt held until the current turn finishes. Type `/later <prompt>` while the agent is working - it queues as a command, so it runs as a fresh turn after the current one ends instead of being injected mid-turn.
user-invocable: true
disable-model-invocation: true
argument-hint: <prompt to run after the current turn>
---
$ARGUMENTS
