# Decorative Graphics & Living Backgrounds

Background graphics that fill empty space and keep the background from being dead.

## The principle

**Any background element is alive by default, not static.** Gradients/blobs drift (breathe). Particles / grids / patterns react to the cursor. A static background is the exception, not the norm. The only thing that always stays static is noise/grain — its movement is visual garbage; it is a texture.

## The six

- **Noise / grain** — static texture at 3–5% opacity. Removes "digital sterility". Cheap, safe. SVG `feTurbulence` or PNG.
- **Geometric pattern** — dots / lines / grid. Structures the background. Must fade under text (mask / opacity).
- **Gradient blobs** — large blurred color shapes, slow drift (8–12s). Heavy `blur` → mobile fallback (reduce radius or make static).
- **Floating particles** — few and slow. A background whisper, not a fireworks.
- **Reactive grid** — nodes respond to the cursor. Award-level. On touch: static or removed.
- **Shader gradient** — liquid flowing background (Stripe-class). The most premium; WebGL; heavy.

## Cross-cutting rules

- The background is the background — it works the atmosphere, never competes with content. If a background element is brighter/faster than the text, it has hijacked attention — that is a failure.
- Anything with blur / particles / WebGL needs a mobile fallback.
- All living backgrounds go through the survey — Claude proposes, the user confirms.

## Degradation ladder

Heavy techniques define their own fallbacks as part of the technique, not as an afterthought. Specify, top to bottom: full experience → reduced-motion alternate (designed static, `motion.md`) → no-WebGL / low-GPU path → touch/no-hover path → no-JS baseline. The page is correct and on-brand at every rung. A technique whose fallback wasn't designed isn't finished.

## Status

- Noise/grain: **SITUATIONAL** (static, safe).
- Living backgrounds (blobs, particles, reactive grid, shader gradient): **SITUATIONAL** — proposed in survey; reactive grid and shader gradient lean Statement.
