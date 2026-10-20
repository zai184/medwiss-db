# Coding Standards

## Core Principles
- clarity over cleverness
- explicit over implicit
- simple over abstract
- deterministic over magical
- readable over concise

## File Size
- prefer files under 300 LOC
- split files before they become multi-domain
- avoid god-components and god-services

## Naming
- use descriptive names
- avoid abbreviations unless universally known
- functions should describe actions
- variables should describe data
- avoid generic names like `data`, `utils`, `helpers`

## Functions
- functions should do one thing
- prefer pure functions where possible
- avoid hidden side effects
- avoid boolean flag parameters
- early returns preferred over nested conditionals

## Comments
- comment why, not what
- avoid redundant comments
- remove outdated comments immediately
- do not narrate obvious code

## Errors
- fail loudly and clearly
- use typed errors where appropriate
- error messages must be actionable
- avoid catch-all error handling

## Testing
- test observable behavior
- test edge cases explicitly
- avoid implementation-coupled tests
- bug fixes require regression tests
- no flaky tests

## Formatting
- enforce formatting with tooling
- avoid manual formatting debates
- keep imports organized
- remove unused imports immediately

## Dependencies
- prefer standard library first
- add dependencies only with clear justification
- avoid overlapping libraries
- prefer actively maintained libraries
- minimize transitive dependency complexity
