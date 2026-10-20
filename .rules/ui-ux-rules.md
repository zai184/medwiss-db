# UI/UX Rules

## Components

- One component per file
- Keep them focused on one thing
- Split when they get confusing, not at some arbitrary line count

## State

- Lift state when components share it
- Derive, don't duplicate
- Use the URL for shareable state

## Forms

- Validate on submit
- Show errors clearly
- Don't lose user data on errors

## Styling

- Pick ONE approach (CSS modules, CSS-in-JS, whatever)
- Be consistent
- Don't mix approaches in the same project

## Performance

- Lazy load routes
- Optimize images
- Test on slow devices

## Error Handling

- Surface errors visibly
- Provide recovery actions
- Don't pretend everything is fine

## Accessibility

- Keyboard navigation works
- Screen reader tested
- Color isn't the only signal

## What NOT to Do

- Don't create abstractions for "flexibility" nobody asked for
- Don't chase the latest React pattern
- Don't optimize before measuring

---

**Reality check:** If users can't figure out your UI without a tutorial, it's broken. Fix the UI.
