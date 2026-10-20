# Git Workflow

## Branches
- main: production-ready code only
- feature/*: new features
- fix/*: bug fixes
- refactor/*: code improvements
- delete branches after merge

## Commits
- write atomic commits
- use conventional commits format
- keep commit messages under 72 characters
- explain why, not what, in body
- reference issue numbers when applicable

## Pull Requests
- keep PRs small and focused
- one logical change per PR
- require at least one review
- all CI checks must pass
- resolve conflicts before requesting review

## Code Review
- review within 24 hours
- focus on correctness and maintainability
- approve only when you understand the changes
- use suggestions for minor fixes
- separate style from substance feedback

## Merging
- use squash merge for feature branches
- use regular merge for release branches
- delete source branch after merge
- ensure clean linear history on main

## Pre-commit
- run linting automatically
- run type checking
- run tests
- format code consistently

## Commit Messages
```
type(scope): subject

body (optional)

footer (optional)
```

Types: feat, fix, docs, style, refactor, test, chore, perf, ci

## Protected Branches
- require PR reviews on main
- require status checks to pass
- prevent force pushes
- prevent deletion
- require linear history

## Tags
- tag all releases semantically (v1.2.3)
- annotated tags for releases
- lightweight tags for internal marks
- push tags with `git push --follow-tags`

## Rebasing
- rebase feature branches on main before merge
- never rebase shared branches
- resolve conflicts during rebase
- force push only to personal branches
