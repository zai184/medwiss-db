# Observability

## Logging

- Structured logs (JSON) when you need to query them
- Plain text is fine for local dev
- Include context: what, when, who
- Never log secrets or PII

## Errors

- Catch and log all errors
- Include stack traces
- Group similar errors
- Fix the noisy ones

## Metrics

- Measure what users care about (latency, errors)
- Measure what you need to debug (queue depth, DB connections)
- Don't measure everything - it's noise

## Alerting

- Alert on symptoms, not causes
- If it pages at 3am, it better be actionable
- Test your alerts work

## What NOT to Do

- Don't build distributed tracing for a monolith
- Don't log everything "just in case"
- Don't alert on "interesting" - alert on "broken"

---

**Reality check:** If you have 47 dashboards and still can't find bugs, delete 46 dashboards. Observability is about finding problems, not building pretty graphs.
