# Forbidden Patterns

## Security
- never disable RLS
- never store auth tokens in localStorage
- never commit secrets
- never expose server environment variables to the client
- never trust client authorization
- never build SQL queries via string concatenation

## Architecture
- no business logic in UI components
- no direct database access from frontend code
- no duplicated API types
- no circular dependencies
- no hidden global mutable state
- no framework lock-in inside domain logic

## Code Quality
- no `any` in TypeScript
- no giant utility files
- no dead code accumulation
- no silent catch blocks
- no copy-paste programming
- no speculative abstractions
- no magic numbers without context
- no boolean trap APIs

## AI Anti-Patterns
- no placeholder implementations in production code
- no fake mocks pretending to be real integrations
- no invented APIs or methods
- no generated code without verification
- no TODOs replacing actual implementation

## Performance
- no unbounded loops over external datasets
- no synchronous blocking in request handlers
- no repeated identical queries in hot paths
- no excessive client-side hydration

## Process
- no undocumented architectural decisions
- no schema changes without migrations
- no breaking API changes without coordination
- no dependency additions without justification
