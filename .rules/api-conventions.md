# API Conventions

## HTTP

- GET for reads, POST for writes
- Return 200 for success, 400 for user error, 500 for your error
- Everything else is optional

## Responses

- Return JSON
- Be consistent (pick a shape, stick to it)
- Include enough context to debug

## URLs

- Use nouns: `/users` not `/getUsers`
- Logical nesting: `/users/123/orders`
- Version when you break things: `/v1/users`

## Validation

- Fail fast at the boundary
- Return all errors at once (don't make users play whack-a-mole)
- Invalid is invalid - don't guess what they meant

## Documentation

- Document the hard parts
- Skip the obvious (don't explain what GET does)
- Keep examples working

## What NOT to Do

- Don't bikeshed status codes (422 vs 400 doesn't matter)
- Don't version prematurely
- Don't return 200 with error bodies

---

**Reality check:** If developers can't figure out your API in 5 minutes, it's wrong. Fix the API, not the docs.
