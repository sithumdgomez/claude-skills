---
name: ui-ux-designer
description: Translates an approved brand concept into full UI layouts inside Figma, grounded in visual design theory (Gestalt principles, color psychology, visual hierarchy, whitespace, accessibility) rather than aesthetic guessing. Use when the user wants to design screens/mockups/interfaces in Figma, translate a brand into a UI, create a reviewable design artifact before code, or references a client's Figma file. Works via the Figma MCP server. Also usable as a support sub-skill: `brand-developer` can invoke it once a concept direction is approved, and it hands off to `frontend-design`/`build-premium-website` for the code stage.
argument-hint: [client/project context, or Figma file link if one exists]
---

# UI/UX Designer

A Figma-native design skill: takes an approved brand concept and turns it into real, reviewable interface layouts — grounded in named, citable visual-design theory, not "make it look nice." This is a distinct stage from both brand strategy and code: it owns the *interface layout* deliverable, produced as an actual Figma file the client can review before anyone writes a line of code.

## Where this fits in the pipeline

- **`brand-developer`** owns strategy and concept direction (positioning, palette, typography, logo). Pull brand tokens and the approved concept from there (or from `brand-guidelines` for DVC's own identity) rather than inventing new ones — if no established brand context exists yet, say so and suggest running `brand-developer` first.
- **This skill** owns translating that approved direction into full interface layouts in Figma.
- **`frontend-design`** / **`build-premium-website`** own the code stage — once a Figma layout is approved, hand off to one of those. This skill never writes code.

Other skills can invoke this one as a sub-skill (via the Skill tool, name `ui-ux-designer`) once a concept is locked and a Figma deliverable is needed, or read this file directly for the design-theory checkpoints without running the full Figma-generation flow.

## Prerequisite check — do this before anything else

1. Confirm the Figma MCP server is connected (remote server via `/plugin` → "figma server", or the desktop Dev Mode MCP toggle). If not connected, walk the user through setup before proceeding.
2. Confirm write-to-canvas access: creating/modifying Figma content requires a **Full or Dev seat on a paid Figma plan** — the free tier is read-only. Check this explicitly; don't discover it mid-task. If the user only has read access, say so and offer to produce a detailed layout spec instead (for a human to build in Figma) rather than failing silently partway through.

## Design process

Every layout decision below should trace back to a named principle — if you can't name which one justifies a choice, that's a sign it's aesthetic guessing, not design.

**1. Visual hierarchy** — before laying anything out, decide explicitly what the eye should see first, second, and third. Every subsequent decision (size, color, position) serves this order.

**2. Gestalt checkpoints** — apply directly, not as vague inspiration:
- **Proximity**: group related elements, separate unrelated ones
- **Similarity**: consistent styling signals "these behave the same way"
- **Continuity**: align elements so the eye flows naturally through the hierarchy from step 1
- **Closure**: incomplete shapes/patterns the eye still recognizes (used deliberately, not accidentally)
- **Figure-ground**: make sure primary content reads clearly against its background at every state (hover, dark mode, overlay)

Well-organized interfaces following these principles measurably cut user error rates — treat them as functional requirements, not decoration.

**3. Color** — check every color choice against the brand's actual tone from Discovery, not personal preference. Color carries psychological association (e.g. blue reads trust/calm, red reads urgency) — the palette should reinforce the brand's intended perception, not fight it.

**4. Typography** — build an actual type scale (not just a font pick) structured the same way `frontend-design`'s token system expects it, so handoff to code doesn't require reinventing the scale.

**5. Whitespace** — treat it as a deliberate hierarchy tool that groups related content and lets the eye rest, not leftover space between elements.

**6. Accessibility** — contrast ratios and tap-target sizes get checked now, at the design stage, not caught later in code review.

## Output

Generate the actual Figma frames, components, and variables via the MCP write-to-canvas capability — structured with auto-layout and named variables (color, type scale, spacing) so they map cleanly onto a token system when handed to `frontend-design`/`build-premium-website`, rather than as one-off unstructured layers.

Present the result as a reviewable artifact: walk through which hierarchy/Gestalt/color decision justifies each major layout choice, so a client (or you) can approve based on stated reasoning, not just a gut reaction.

## Common pitfalls

- Generating a layout with no stated rationale — if you can't say which principle justifies a choice, stop and reconsider it
- Skipping the check for existing brand tokens/concept direction and inventing a new look from scratch
- Presenting one polished screen as the whole solution — address responsive breakpoints and key states (empty, loading, error) before calling it done
- Hitting the paid-seat wall mid-task because write access wasn't confirmed first
- Writing code here — that's explicitly out of scope; hand off to `frontend-design` or `build-premium-website` once the Figma layout is approved
