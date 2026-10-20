# Release Process

## Principles

- Ship when it's ready, not when the calendar says
- Smaller releases beat big bangs
- Rolling back must be faster than fixing forward

## Before Shipping

**Required:**
- Tests pass
- Works on your machine AND staging
- You know how to roll back

**Good to have:**
- CHANGELOG updated (helps debugging later)
- Someone else looked at it

## Deployment

1. **Staging first** - obvious, but people skip it
2. **Watch metrics for 30 minutes** - error rates, latency
3. **If it breaks** - rollback first, investigate later

## Hotfixes

- Branch from the broken release tag
- Fix, test, ship
- Merge back to main immediately
- Don't let hotfixes become permanent branches

## What NOT to Do

- Don't ship Friday at 5pm
- Don't deploy 20 changes at once
- Don't "monitor overnight" - automate alerts or accept the risk

## Versioning

Use semver if you have users who care. Otherwise, git tags work fine.

---

**Reality check:** If your release process needs a 3-day checklist, your system is too fragile. Fix the system.
