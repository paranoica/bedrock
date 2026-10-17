# Pattern: Profile / Account

This file gives Claude what to assemble, not what to copy. An application surface.

## 1. Purpose
Let a user view and manage their own data — identity, settings, account actions.

## 2. Block composition
**Required:** an identity block (avatar/initials, name), editable fields/sections, a save mechanism.
**Optional:** tabbed sections (profile / security / billing / notifications), an avatar uploader, dangerous-action zone (delete account), activity history.

## 3. Order logic
Identity at the top → most-used settings next → rarely-used and dangerous actions last. Dangerous actions (delete account) are visually separated and placed at the end, never near routine controls.

## 4. Variants by mode
Profile leans Clean structurally — predictability over flair. Polish lives in smooth field transitions, the save state, tab sliding.

## 5. Technique bindings
- Forms follow `principles/forms.md` (label-above, inline validation, concrete errors).
- Avatar follows `principles/photography.md` (fixed ratio, object-fit cover, initials-fallback).
- Dangerous actions follow the forms dangerous-action rules — strong confirmation or undo (`principles/forms.md`).
- Tabs: sliding active indicator (`principles/motion.md`).
- Save action: button with idle/loading/done states (`principles/motion.md`).
- Empty/error states per section (`principles/screen-states.md`).

## 6. Typical mistakes
- Delete-account one click away with no strong confirmation.
- Dangerous actions sitting beside routine settings.
- A save with no loading/done feedback — the user does not know it worked.

## 7. The hook in this section
Carry the site's hook through this section too, not just the hero (`principles/concept.md`): state per build how it advances the one central idea, or how it stays deliberately quiet so the hook lands elsewhere.
