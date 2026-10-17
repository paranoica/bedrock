# Pack: Frontend

## Rules
- Accessible by default: labels, roles, focus order, contrast; keyboard reaches everything.
- No `innerHTML` or `dangerouslySetInnerHTML` with outside data.
- Loading, empty and error states for every data view.
- The design work itself goes to design-creator.

## Critical zones to consider
Checkout and payment screens, auth forms, anything that deletes on click.

## Reviewer checklist
- Core Web Vitals on touched pages; bundle size delta.
- No layout shift from late-loading content.
- Text fits at 375 px and at 200 % zoom.

## Test checklist
- E2E for the main paths with role or test-id locators (the `e2e` skill).
- Screenshots at 375, 768 and 1280 px; an axe scan; the flow by keyboard only.
