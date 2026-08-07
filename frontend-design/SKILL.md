---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, or applications. Generates creative, polished code that avoids generic AI aesthetics.
argument-hint: [component, page, or interface to build]
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

## For other skills that want to use this one

There are two valid ways another skill can lean on this one — pick whichever fits:

1. **Invoke it as a sub-skill** (via the Skill tool, name `frontend-design`) when a workflow has already settled the brand/content strategy and just needs the aesthetic execution — e.g. `brand-developer`'s Technical Translation/Build step, or `build-premium-website`.
2. **Read this file directly** when you just need the aesthetic guidelines as a reference.

If a `brand-guidelines` or `brand-developer` skill is present and relevant (a client engagement with an established brand), check those first for the client's actual color/type tokens and platform decision — this skill governs execution craft, not brand strategy or platform choice.

## Design Thinking

Before coding, understand the context and commit to a BOLD aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it? What's the strategic outcome (recognition, trust, conversion) the aesthetic choices need to serve — not just "looks good"?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Platform target**: Confirm the tech stack and whether this ships as hand-written code or through a no-code/low-code builder — each has different constraints on how styles and structure should be organized, so confirm before starting rather than translating after the fact.
- **Usability**: Is navigation clear? Does it perform well and stay accessible? This isn't secondary to aesthetics — it's roughly a third of how design work is actually judged professionally.
- **Content**: Write actual copy in the real voice, not lorem ipsum — human, specific copy consistently outperforms generic placeholder-driven design.
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Frontend Aesthetics Guidelines

Focus on:
- **Typography**: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics; unexpected, characterful font choices. Pair a distinctive display font with a refined body font.
- **Color, Type & Spacing as one token system**: Don't just set color as CSS variables — define color, type scale, and spacing as one linked token system. This is what lets a design actually hold together as a real system across multiple pages/components instead of looking designed only in isolation. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
- **Motion**: Reach for the **View Transitions API** for page/state transitions (name matching elements across states and the browser morphs between them automatically, no JS needed) and CSS Scroll-Driven Animations for scroll-tied effects — both have strong but not universal support (~87% desktop, ~71% mobile as of 2026), so pair with a simple fallback transition rather than assuming support everywhere. Escalate to GSAP/Motion only for complex timeline choreography CSS can't handle, and tune easing curves deliberately. Every animation should confirm an action, guide attention, or clarify a flow — cut anything that's decoration without one of those jobs. See `reference.md` for working syntax on both.
- **Spatial Composition**: Purpose-driven, not decorative — whitespace and restraint should serve clarity, not just look clean. Favor natural, asymmetric composition over rigid grid-perfection. Within a minimal system, let typography (oversized, expressive, sometimes animated) carry the brand's personality — that's what "minimal" and "distinctive" both at once actually looks like. Watch for over-neutral minimalism: restraint that erases tone makes a brand feel interchangeable, not refined.
- **Responsive Systems**: Build to adapt at the component level (CSS container queries), not just page-level breakpoints — fluid across arbitrary widths rather than jumping between fixed sizes. See `reference.md` for container query syntax.
- **Backgrounds & Visual Details**: Create atmosphere and depth rather than defaulting to solid colors. Add contextual effects and textures that match the overall aesthetic. Apply creative forms like gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, custom cursors, and grain overlays.
- **Icons & Elements**: Generic icon libraries (Lucide, Font Awesome, Material defaults) are fine for internal tools, dashboards, or MVPs where speed matters more than distinctiveness — but for consumer/brand-facing work they're the icon equivalent of Inter-and-purple-gradients: seen, not felt, and identical to every other product using the same defaults. Favor custom or curated-distinctive, detail-rich icon styles for anything brand-facing, and run icons through the same token system as color/type (consistent stroke weight, grid, corner radius) rather than mixing library defaults with custom marks.

NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial, system fonts), cliched color schemes (particularly purple gradients on white backgrounds), predictable layouts and component patterns, generic icon sets on brand-facing work, and cookie-cutter design that lacks context-specific character.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

Remember: Claude is capable of extraordinary creative work. Don't hold back, show what can truly be created when thinking outside the box and committing fully to a distinctive vision.
