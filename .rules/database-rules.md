# Database Rules

## Schema

- Pick a naming convention, stick to it
- Every table needs an id, created_at, updated_at
- Foreign keys: `parent_table_id`
- Document non-obvious relationships

## Migrations

- One change per migration
- Never modify deployed migrations
- Keep them reversible
- Test on production-like data

## Queries

- Use a query builder or ORM
- No raw SQL in application code (migrations excepted)
- Avoid SELECT *
- Index what you query on

## Data Integrity

- Use database constraints
- Enforce NOT NULL on required fields
- Validate enums at DB and app level

## Performance

- EXPLAIN slow queries
- Add indexes for WHERE, JOIN, ORDER BY
- Avoid N+1 queries
- Paginate large results

## Security

- Enable RLS
- Use least-privilege DB users
- Encrypt sensitive data
- Hash passwords, never store them

## What NOT to Do

- Don't bikeshed naming (singular vs plural doesn't matter)
- Don't denormalize without measuring
- Don't build a cache you don't need

---

**Reality check:** Your database will outlive your application code. Design for the next engineer, not the current framework.
