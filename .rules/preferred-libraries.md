# Preferred Libraries

## Principle

**Standard library first. Add dependencies only when they save significant time.**

Every dependency is a liability:
- Supply chain risk
- Version conflicts
- Breaking changes
- Abandoned projects

## When to Add Dependencies

**Worth it:**
- Database drivers (you're not writing postgres protocol)
- Validation (zod, pydantic)
- Testing frameworks (vitest, pytest)

**Questionable:**
- State management (use built-in first)
- HTTP clients (fetch/httpx usually fine)
- Date libraries (Intl API exists)

**Probably wrong:**
- Utility libraries (lodash, ramda)
- CSS frameworks when vanilla CSS works
- "Micro" libraries that save 10 lines

## Infrastructure

- `uv` for Python
- `bun` for JS
- `flake.nix` for system deps
- Docker for services

## What NOT to Do

- Don't add a library because you saw it on Twitter
- Don't add dependencies "just in case"
- Don't use a library for something the standard library does fine

---

**Reality check:** If you can't explain why you need a dependency, you don't need it. Every import is a commitment.
