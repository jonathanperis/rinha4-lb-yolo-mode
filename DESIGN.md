# DESIGN

## Scene
An engineer is checking a Rinha4 transport experiment late at night on a desktop monitor. The page is a control bench for deciding whether a new assembly load balancer is safe to promote. Dark mode fits the scene, but the interface must be calm enough for docs reading.

## Visual Direction
Instrument bench, not terminal cosplay. Use a dark graphite base with copper, cyan, and violet signals. Topology lines, tables, and command blocks carry the visual identity. Motion is minimal and never blocks reading.

## Color Strategy
Full palette, source-backed and restrained in area:

- Background: tinted graphite OKLCH neutrals.
- Primary text: warm off-white.
- Muted text: blue-gray.
- Copper: C baseline and warnings.
- Cyan: proxy/fdpass transport lines.
- Violet: assembly challenger.
- Red: failures and regressions only.

## Typography
- Body: Archivo for readable long-form docs.
- Code and instruments: Sometype Mono.
- Headings: Archivo with tight tracking, not glitch effects.

## Components
- Navigation: padded, non-clipping, clear focus states.
- Hero: proof statement plus adjacent topology/proof rail.
- Evidence modules: labeled status, not decorative metric cards.
- Docs shell: fixed sidebar on desktop, drawer on mobile, high-contrast content.
- Code blocks: readable, scrollable, copy-friendly spacing.

## Accessibility
- No global flicker.
- Respect reduced motion.
- Visible focus outlines.
- Body copy line length around 65 to 75 characters.
- Tables and long code blocks must not force page overflow.
