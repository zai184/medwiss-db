# AI Rules

## General
- think before coding
- state assumptions explicitly
- prefer the simplest implementation that works
- avoid speculative abstractions
- touch only code related to the task
- preserve existing project conventions
- all changes must be traceable to user requirements

## Architecture
- prefer server-side execution over client-side execution
- prefer server actions over REST endpoints when possible
- business logic must not live in UI components
- shared types must be centralized
- never duplicate API contracts
- separate domain logic from framework code
- avoid circular dependencies
- use dependency injection only when needed
- prefer composition over inheritance

## Type Safety
- use strict TypeScript
- never use `any`
- prefer discriminated unions
- validate all external input
- Zod is the single source of truth for types
- use zod validation everywhere
- infer types from schemas when possible
- never trust client-side types

## Data
- use migrations for all schema changes
- database schema is the source of truth
- never mutate data shapes silently
- prefer immutable transformations
- never perform hidden data coercion

## Frontend
- keep components small and single-purpose
- avoid deeply nested state
- derive state instead of duplicating it
- avoid prop drilling when composition solves it
- no business logic inside presentation components
- prefer progressive enhancement
- optimize for accessibility first

## Backend
- keep handlers thin
- business rules belong in services/domain layer
- all external requests require timeouts
- retry logic must be explicit
- log failures with actionable context
- never swallow errors silently

## Security
- never disable RLS
- never use localStorage for auth tokens
- never expose secrets to the client
- source API keys from shell environment
- validate authorization server-side
- sanitize all user input
- use parameterized queries only
- avoid dynamic SQL generation
- use secure cookies for auth
- enforce CSRF protection where applicable

## AI Workflow
- do not invent APIs
- do not assume library behavior
- verify generated code against docs
- prefer existing project patterns over new abstractions
- avoid generating placeholder implementations
- avoid TODO-driven development
- generated code must be production-ready unless explicitly stated otherwise

## Documentation
- update CHANGELOG.md after code changes
- update AGENTS.md when workflow changes
- document non-obvious architectural decisions
- document assumptions and tradeoffs
