# Pattern: Navbar

This file gives Claude what to assemble, not what to copy.

## 1. Purpose
Persistent navigation. Lets the visitor know where they are and move anywhere, without stealing attention from content.

## 2. Block composition
**Required:** logo / wordmark, primary nav links, a primary action (CTA or account).
**Optional:** secondary links, search, theme toggle, a mega-menu, a mobile burger (required below the nav breakpoint).

## 3. Order logic
Logo left (anchor / home) → nav links center or left-grouped → primary action right. This is the scan order users expect; deviating from it costs orientation.

## 4. Variants by mode
- **Clean** — flat bar, thin border or subtle surface, calm.
- **Statement** — may transform on scroll (shrink, change surface), bolder type; an animated active-link indicator that slides.

## 5. Technique bindings
- Active indicator moves animatedly, never jumps (`principles/motion.md`).
- Burger ↔ cross via Level-1 icon morphing (`principles/icon-morphing.md`).
- Mobile collapse to burger is one of the six breakpoint checks (`principles/responsive.md`).
- Theme toggle ties to `principles/theming.md`.
- Any dropdown/mega-menu obeys the universal overlay rule (`principles/micro-mechanics.md`).

## 6. Typical mistakes
- Nav that does not collapse to a burger on mobile.
- Active state that jumps between links instead of sliding.
- A dropdown that does not close on outside-click / Escape.
- Logo not linking home.

## 7. The hook in this section
Carry the site's hook through this section too, not just the hero (`principles/concept.md`): state per build how it advances the one central idea, or how it stays deliberately quiet so the hook lands elsewhere.
