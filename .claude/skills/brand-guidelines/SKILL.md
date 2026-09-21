---
name: brand-guidelines
description: Applies Design Vibes Collective's official brand colors, typography, and visual identity to any artifact — decks, documents, web pages, social graphics, or presentations. Use whenever the user wants brand colors applied, a "Design Vibes Collective" or "DVC" look, on-brand styling, or is producing client-facing/marketing material for this agency.
argument-hint: [artifact type — deck / doc / web page / social graphic]
---

# Design Vibes Collective Brand Styling

## Overview

Design Vibes Collective (DVC) is a design agency — the brand identity below is sourced directly from the agency's own brand guideline deck (`~/Downloads/DVC presentation.pdf`), not a generic placeholder. Apply it whenever an artifact should carry DVC's identity.

**Keywords**: branding, corporate identity, visual identity, styling, brand colors, typography, Design Vibes Collective, DVC, visual formatting, visual design

**When NOT to use this:** this skill applies *DVC's own* identity to *DVC's own* material. It is **not** for developing or styling a **client's** brand — never stamp DVC's orange, Borna, or sunburst onto a client project. For creating or applying a client's brand identity, use `brand-developer` (for the client's own tokens) instead.

## Brand Identity

**Tagline**: "We Bring Ideas to Life"
**Positioning**: "Igniting the visions of design trailblazers through dynamic branding and digital prowess"
**Voice/personality**: Creative, Professional, Approachable — bold and declarative in headlines ("WE CREATE LEGENDS"), warmer and more conversational in supporting copy. Not corporate-stiff; confident without being try-hard.

## Colors

**Core:**

| Role | Hex | RGB | CMYK |
|---|---|---|---|
| Black (primary text/dark) | `#000000` | 0, 0, 0 | C75 M68 Y67 K90 |
| Orange (primary accent) | `#FF3C00` | 255, 60, 0 | C0 M89 Y100 K0 |
| White | `#FFFFFF` | 255, 255, 255 | C0 M0 Y0 K0 |
| Light Gray (backgrounds) | `#F1F2F2` | 241, 242, 242 | C4 M2 Y3 K0 |
| Mid Gray (secondary elements) | `#C7C9C8` | 199, 201, 200 | C22 M16 Y18 K0 |
| Dark Gray (muted text/captions) | `#6D6E71` | 109, 110, 113 | C58 M49 Y46 K15 |

Orange (`#FF3C00`) is the signature accent — used for emphasis words in headlines, CTAs, icons, and the logo mark itself. Don't dilute it by overusing it as a background; it works best as a sharp accent against black, white, or the light gray (`#F1F2F2`).

## Typography

- **Heading**: Borna, Bold. This is the brand's distinctive display face — bold, condensed-leaning, used for large declarative statements ("WE BRING IDEAS TO LIFE").
- **Subheading**: Archivo, Semibold.
- **Body/Paragraph**: Archivo, Regular.

**Fallbacks** (when Borna/Archivo aren't installed in the target environment): Borna → a bold grotesk/sans (Arial Bold, Helvetica Bold); Archivo → Arial/Helvetica for both semibold and regular weights. Note the substitution to the user if fonts aren't available rather than silently degrading quality.

## Visual Motifs

- **Sunburst/radial icon**: a circular burst of straight rays (alternating orange/black or solid orange), used as a standalone graphic element and page accent — not just decoration, it's a recurring brand mark.
- **Logo mark**: a stylized angular "D" in orange, paired with "DESIGN VIBES COLLECTIVE" wordmark (bold "DESIGN" + regular "VIBES" + "COLLECTIVE" beneath). Three lockup variants: horizontal (icon + wordmark side by side), vertical (icon above stacked wordmark), and circular badge (icon centered in a ring reading "DESIGN VIBES COLLECTIVE · WE BRING IDEAS TO LIFE").
- **Photography**: high-contrast black-and-white, often extreme close-ups (eyes, texture) — moody and editorial rather than bright/corporate stock photography.
- **Layout language**: thin hairline rules, grid-visible layouts (visible column/row guides as a design device, not just backend structure), plenty of negative space, orange used sparingly but decisively.

## Applying This to an Artifact

- **Presentations (PPTX)**: Borna Bold on headings, Archivo for body/subheads, orange for one emphasized word/phrase per headline (not the whole line), light gray or white backgrounds, black for primary body text.
- **Documents (DOCX)**: same type hierarchy; use the dark gray (`#6D6E71`) for captions/metadata rather than a washed-out light gray, which reads poorly in print/paper contexts.
- **Web/HTML artifacts**: orange as the accent/CTA color against black or `#F1F2F2` backgrounds; reserve pure white for content cards floating on the light gray base, mirroring the deck's own site mockups. Note: on claude.ai Artifacts the CSP blocks font CDNs, so Borna/Archivo must be embedded as `@font-face` data URIs — a linked Google-Fonts/CDN URL silently falls back. Embed the faces or the artifact won't actually render in-brand.
- **Social/marketing graphics**: the sunburst motif and bold cropped photography are signature enough to use even without the full wordmark, if space is tight.

Always ask which artifact type this is for if it's ambiguous — the color/type choices above are consistent, but density and hierarchy should adapt (a slide needs bigger, sparser type than a document).
