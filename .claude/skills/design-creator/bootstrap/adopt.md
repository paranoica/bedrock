# Adopt — working on an existing frontend

Loaded when a frontend already exists (Stage 2 scaffold is skipped). Its job: make the engine **read the project's design, not reinvent it**, so new work lands in the same style instead of "close but not quite". When an AI infers visual decisions from scattered hardcoded values, every session drifts; reading a token contract instead of inferring is what keeps output consistent.

## Conform before improving (MUSTHAVE-BASE)

On an existing project the engine **obeys the found system by default**. It does not impose a new hook, mode, or archetype. "Improve / redesign" happens only when the user explicitly asks — and then as a separate, named step, not smuggled into a small edit.

## Extract the de-facto token contract

Before building, derive the project's real tokens from its CSS / Tailwind config / component library and write them to `.design/tokens.json` (the committed contract Stage 3 reads):

- color ramp(s), neutral scale, accent(s)
- type scale, font roles, line-heights
- spacing scale, radii, shadow/elevation steps
- motion timings/easings

Detect an existing component library (shadcn / Radix / MUI / headless primitives) and **restyle on top of its primitives** rather than building parallel components. Where the codebase is inconsistent (multiple ad-hoc values), surface the drift and propose a consolidated scale — don't silently pick one.

*(Full extraction + audit mechanics and the component-library detection are expanded below.)*

## Extraction audit (how to read the de-facto system)

1. **Scan the sources** in priority order: design-token files / Tailwind config / CSS custom properties → component library theme → computed styles of representative components.
2. **Cluster, don't copy.** Real codebases drift (six near-identical greys, four button paddings). Cluster near-duplicates into the intended scale and record the canonical value; flag the drift for the user rather than enshrining every variant.
3. **Derive the contract**: write `.design/tokens.json` with color ramps, type scale, spacing, radii, elevation, motion — the single source Stage 3 and the QA gate read.
4. **Capture the conventions too**: file/folder layout, naming, state patterns, the existing motion feel — new work must match these, not just the colors.

## Component-library awareness

Detect an existing primitive layer (shadcn/ui, Radix, Headless UI, MUI, Mantine, Chakra) and **restyle on top of it** — theme the primitives, compose from them — instead of building a parallel component set. Two parallel button systems is the failure. Match the library's API and accessibility behavior; only introduce a new primitive when none exists for the need.

## Multi-target tokens (W3C DTCG)

Keep one canonical, tool-agnostic token file (W3C Design Tokens / DTCG shape) as the source, and generate the targets the project needs from it: CSS custom properties, a Tailwind theme, a JS/TS object, and a Figma-importable set. One contract, many outputs, so design and code never drift apart. This is the same `.design/tokens.json` that the `.gitignore` policy keeps committed.

## Conform-guard

On an existing project the engine runs a standing **conform-guard**: before shipping any new section, it checks the new tokens/spacing/motion against the extracted contract and blocks anything that introduces an off-system value. "Improve the system" is a separate, explicitly-requested mode — never silent drift dressed up as a small edit.

## Status

Conform-before-improve, read-don't-invent, restyle-on-existing-primitives: **MUSTHAVE-BASE** whenever a frontend already exists.
