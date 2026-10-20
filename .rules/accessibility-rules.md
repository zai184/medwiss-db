# Accessibility

## The Goal

Real people use assistive technology. Make it work for them.

## Must Work

- Keyboard navigation (Tab, Enter, Escape)
- Screen readers (test with NVDA or VoiceOver)
- Focus visible and logical

## Checklist (Do These)

- Heading hierarchy makes sense (h1 → h2 → h3)
- Form labels associated with inputs
- Alt text for meaningful images (empty for decorative)
- Color isn't the only way to convey information
- Touch targets at least 44x44px

## Respect User Preferences

- Honor `prefers-reduced-motion`
- Don't autoplay media
- No flashing content

## Testing

- Tab through your app regularly
- Try a screen reader once per release
- Automated tools (axe) catch obvious stuff

## What NOT to Do

- Don't treat WCAG as a checklist to pass
- Don't rely on automated testing alone
- Don't assume "disabled users are a small percentage"

---

**Reality check:** Accessibility isn't a feature. It's basic engineering. If a blind user can't use your app, you built it wrong. Fix it.
