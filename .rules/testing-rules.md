# Testing Rules

## Philosophy
- tests exist to prevent regressions, not to achieve coverage targets
- test behavior, not implementation
- one test file per source module

## Structure
- use vitest for TypeScript/JavaScript
- use pytest for Python
- use built-in test for Rust
- use testing package for Go

## Unit Tests
- test public interfaces only
- mock external dependencies, not internal logic
- keep tests deterministic (no randomness)
- one assertion per concept

## Integration Tests
- test at the API boundary
- use real database in Docker for data tests
- clean state between tests
- parallelize where possible

## E2E Tests
- use Playwright for web apps
- test critical user journeys only
- avoid testing implementation details
- run against staging, not production

## Test Data
- use factories, not fixtures
- generate test data programmatically
- never rely on production data
- seed data should be minimal

## Naming
- describe what is being tested
- include the expected outcome
- format: `it('should [action] when [condition]')`
- avoid `test1`, `test2` naming

## Coverage
- focus on critical paths
- 100% coverage of domain logic
- exclude generated code from coverage
- coverage thresholds in CI only

## Flakiness
- retry logic belongs in the code, not tests
- fix flaky tests immediately
- never disable tests to "fix" later
- isolate time-dependent tests

## Debugging
- failing tests must have clear messages
- use descriptive assertion messages
- log relevant context on failure
- minimize test setup complexity
