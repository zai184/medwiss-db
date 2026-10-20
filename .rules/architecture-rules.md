# Architecture Rules

## System Design
- architecture must remain understandable by a new engineer within one day
- optimize for maintainability before extensibility
- avoid premature microservices
- prefer modular monoliths unless scale requires separation

## Boundaries
- UI must not directly access persistence
- API layer must not contain business logic
- domain logic must not depend on frameworks
- infrastructure concerns must remain isolated

## State Management
- server state and UI state must remain separate
- avoid duplicated state sources
- derive state whenever possible
- prefer stateless services

## APIs
- API schemas are contracts
- all APIs must be typed end-to-end
- version breaking changes explicitly
- avoid inconsistent response shapes

## Data Access
- database access must go through a defined layer
- avoid raw queries scattered across the codebase
- transactions must be explicit
- prevent N+1 query patterns

## Async Systems
- all async flows require timeout handling
- all queues/jobs require idempotency
- retries must use bounded backoff
- background jobs must be observable

## Observability
- all critical paths require structured logging
- errors must include context identifiers
- metrics should measure user-impacting operations
- avoid noisy logs

## Performance
- optimize only after measuring
- establish performance budgets
- avoid unnecessary client hydration
- prefer streaming where appropriate

## AI-Generated Code
- generated code must match existing architecture
- generated code must not introduce parallel patterns
- generated code must not bypass shared infrastructure
- generated code must not duplicate domain logic
