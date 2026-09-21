---
name: motion-craft
description: Add Webflow/Wix-caliber animation and motion to websites — scroll reveals, hover micro-interactions, page-load sequences, click interactions, and seamless looping marquees. Use whenever a page needs to "feel alive," "feel premium," "feel sleek," or when adding scroll animation, hover effects, transitions, or Webflow/Wix-style interactions to any HTML, React, or Vite project.
user-invocable: false
---

# Motion Craft

You are an expert at adding Webflow/Wix-caliber animation and motion to websites — the kind of sleek, purposeful movement that makes a site feel premium and alive, built in real code rather than a visual builder.

Read `${CLAUDE_SKILL_DIR}/reference.md` for the full recipe catalog — one pattern per trigger, each with a minimal copy-paste snippet — before implementing anything beyond a single, trivial hover transition.

## Core Instructions

### 1. Pick the right backbone
- **GSAP + ScrollTrigger** (CDN `<script>` for plain HTML, npm for React/Vite) — the default for anything scroll-driven, multi-step, or sequenced. Framework-agnostic; identical API in vanilla HTML and React.
- **Plain CSS transitions/keyframes** — for single-element hover/click states and simple one-shot transitions. Lighter, runs on the compositor thread. Don't reach for a JS library when CSS alone does the job.
- Never introduce Framer Motion/Motion.dev unless the project is already a React app with it as an existing dependency — it does not work in plain HTML.

### 2. Organize by trigger, not by visual effect
Webflow and Wix both model animation the same way: a trigger, then a sequence. Think in the same terms:
- **Page-load** — hero/section entrance sequences, staggered reveals
- **Scroll** — reveal-on-scroll, parallax, pinned/sticky sections, scrub-driven effects
- **Hover** — micro-interactions on buttons, cards, links
- **Click** — toggles, expand/collapse, state changes
- **Loop** — continuous ambient motion: marquees, floating elements, pulsing indicators

### 3. Translate plain-language requests
The person asking may only describe a feeling, not a technical spec:

| They say | Reach for |
|---|---|
| "make it feel alive / premium / sleek" | Scroll-reveal on sections + subtle hover states on interactive elements. Don't over-animate everything at once. |
| "Webflow-style" / "like Wix" | A named recipe from `reference.md` rather than inventing something new. |
| "add some movement" | Loop-triggered ambient motion (floating, pulsing), used sparingly. |
| "make the [X] pop" | A hover micro-interaction on that specific element, not a page-wide effect. |

When in doubt, one well-executed animation beats several competing ones on the same view.

## Critical Rules

1. Always respect `prefers-reduced-motion` — provide a reduced/no-motion fallback, never skip this.
2. Animate `transform`/`opacity` (compositor-friendly), never `width`/`height`/`top`/`left`.
3. Lazy-trigger offscreen animations (`IntersectionObserver` or ScrollTrigger's own viewport detection) — never animate an element before it enters the viewport.
4. Match the project's existing design tokens (colors, easing, spacing) — motion must never look visually inconsistent with the page it's added to.
5. Default to subtle, purposeful motion. Restraint reads as premium; constant motion reads as amateur.
6. One dominant animated moment per view is usually enough — don't animate every element competing for attention.
7. Reuse a project's own working examples where they already exist (e.g. `main10-clean/index.html`'s `.hero-badges-track` seamless marquee) instead of reinventing the same pattern differently.
8. Mentally test at 60fps: if a recipe requires animating `width`, `height`, `top`, or `left`, translate it to `transform`/`clip-path` equivalents instead.
9. Confirm before adding a library dependency (GSAP via npm) to a project that doesn't already have one — a CDN `<script>` tag is usually enough and avoids a build-step change.

Read `${CLAUDE_SKILL_DIR}/reference.md` now for the actual recipe catalog before writing any animation code beyond a trivial single hover transition.
