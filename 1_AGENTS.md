# AGENTS.md — Project Governance & Standards

This file is authoritative for all AI agents (Hermes, OpenCode, etc.) working in this repository.

## System Environment
- OS: NixOS 25.11
- Kernel: 6.12.87
- Arch: x86_64
- CPU: AMD Ryzen 9 5900HX
- GPU: NVIDIA GeForce RTX 3070 Mobile (CUDA 13.0)
- Preferred dependency tools: `uv`, `bun`, `flake.nix`
- Services: Use `docker-compose.yml` for llamaserver, neo4j, etc.
- terminal: kitty
- shell: zsh
- desktop environment: qtile, notifications: dunst
- in shell scripts use #!/run/current-system/sw/bin/zsh
- Always use **systemd services + timers** for recurring or scheduled tasks, do **not** create cron jobs.

## Coding Assistant Obligation
When a task is finished, issue this shell command:
```bash
notify-send " 󰦥  Fertig Boss  󰦥 " --icon=dialog-information && pw-play ~/Dokumente/1_conf/sounds/Bass-C2.wav
```

## Preferred Languages & Stack
- Python, Svelte, TypeScript, Rust, Zig, Go
- Use the best tool for the job while respecting existing architecture.

## AI integration
- Use llama.cpp and llamaserver for local models
- local model: Qwen3.5-9B-Q5_K_M.gguf, alias qwen35-9b, served by llamaserver running in docker container serving on port 8080
- use these remote models:
xai:grok-4.3
xai:grok-build-0.1
openrouter:xiaomi/mimo-v2.5
openrouter:xiaomi/mimo-v2.5-pro
openrouter:qwen/qwen2.5-vl-72b-instruct
openrouter:z-ai/glm-4.5v
opencode-go/kimi-k2.6
opencode-go/glm-5.1
opencode-go/qwen3.6-plus
opencode-go/deepseek-v4-flash
- api keys are set as environment variables. source them as ${LOCAL_API_KEY}, ${XAI_API_KEY}, ${OPENROUTER_API_KEY}, ${OPENCODE_API_KEY}

## Dependencies & Reproducibility
- Prefer `flake.nix` for system-level dependencie
- Use `uv` for Python, `bun` for JS/TS
- All generated code must be reproducible
- Prefer deterministic builds

## Governance Files (Authoritative)
All agents **must** follow these files:

`.rules/`
- `rules.md`
- `coding-standards.md`
- `architecture-rules.md`
- `forbidden-patterns.md`
- `preferred-libraries.md`
- `security-rules.md`

## Documentation Standards
After any significant work:
- Update `CHANGELOG.md` with:
  - Date in format `yyyy-mm-dd hh:mm`
  - Changes made
  - LOC added
  - New total LOC
- Update this `AGENTS.md` when architecture or workflow changes
- Maintain:
  - `docs/architecture.md`
  - `docs/decisions.md`
  - `docs/db-schema.md`
  - `docs/debugging-playbook.md`

## Mandatory Agent Workflows

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

## Architecture & Code Quality
- Always match existing architectural patterns
- Avoid introducing parallel abstractions
- Generate and maintain:
  - System architecture map
  - Data flow diagram
  - API inventory
  - Dependency graph
- All code must pass linting, type checking, and relevant tests

## Source Control & Secrets
- **NEVER** hardcode secrets — always source from environment
- **DON'T** put API keys in .env files!

---

**Last updated:** 2026-05-19
