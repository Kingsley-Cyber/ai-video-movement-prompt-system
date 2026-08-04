# CPCS application facade

This is the stable, headless client boundary over the existing CPCS runtime. One service owns
operation names, validation, permissions, and response envelopes. CLI, MCP, HTTP, guided, and
advanced clients only translate transport input into that service.

## Local command

```bash
./bin/cpcs status
./bin/cpcs intent.normalize <<'JSON'
{"text":"Create a restrained scene where she realizes he is lying"}
JSON
./bin/cpcs intent.context <<'JSON'
{"text":"Show how this device works in a clear educational video","token_budget":12000}
JSON
```

Every call returns `cpcs.application_response/1.0`. Inputs are the operation's `arguments` object;
use `./bin/cpcs --list` to inspect the chat-safe catalog.

Add `--telemetry work/telemetry/application.jsonl` to CLI, MCP, or HTTP processes for content-free
operation timing. Release policy caps context requests at 50,000 tokens, external evidence at 64
items, HTTP bodies at 4 MiB, and one provider build at 32 generated seconds.

## MCP

Run the newline-delimited JSON-RPC stdio server:

```bash
python3 -m lab.application.mcp --role chat
```

It implements `initialize`, `tools/list`, and `tools/call`. The default catalog contains status,
intent, context, reason, score, and non-submitting build tools. Staging, derived, curated, and
immutable operations are absent unless the server process starts with a sufficient role.

## Local HTTP

```bash
python3 -m lab.application.http --host 127.0.0.1 --port 8765 --role chat
curl http://127.0.0.1:8765/v1/status
curl -X POST http://127.0.0.1:8765/v1/invoke \
  -H 'Content-Type: application/json' \
  -d '{"schema":"cpcs.application_request/1.0","operation":"cpcs.intent.normalize","arguments":{"text":"Casual phone product recommendation"}}'
```

The HTTP adapter has no identity provider. Operator and curator roles are therefore restricted to
loopback and are not production authorization.

## Authority profiles

| Role | Operations | Mutation |
|---|---|---|
| `chat` | status, intent, context, reason, score, inline build | none |
| `operator` | chat operations plus extraction, distillation, review, reflection | staging or derived only |
| `curator` | all operations plus promotion and render evidence | curated or immutable, only with request-bound authorization |

An explicit authorization contains the operation and
`authorization_request_hash(operation, arguments)`. Changing one argument invalidates it. This is
a deliberate human-approval boundary, not a substitute for authenticated deployment security.

## Honest limits

- `bin/cpcs` is a repository-local command, not an installed package entry point.
- MCP covers the tools protocol needed by CPCS; it is not yet qualified against multiple MCP hosts.
- HTTP is a local development adapter with a bounded request body, no TLS, identity, sessions,
  quotas, or rate limiting.
- Guided and advanced clients are headless Python calls, not a graphical end-user application.
- Persistent user/project context and live provider qualification remain separate gaps.
