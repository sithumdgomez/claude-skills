---
name: cms-website-builder
description: Builds websites and online stores on WordPress, Wix, or Shopify — theme development, platform-native best practices, and choosing the right one of the three for a given client. Use when the user wants a WordPress site/theme, a Wix site (Studio or Editor), a Shopify store/theme, or needs help deciding which no-code/managed platform fits a project.
argument-hint: [platform (WordPress/Wix/Shopify) and site/store to build]
---

# WordPress / Wix / Shopify Development

You build on managed/no-code platforms — a distinct concern from hand-coded builds (`build-premium-website`, `web-app-development`) or Figma-stage design (`ui-ux-designer`).

## Where this fits with the rest of the toolkit

- Confirm platform as part of `brand-developer`'s existing "platform target" step, or decide here if that hasn't happened yet
- Apply `frontend-design`'s typography/color/motion discipline wherever the chosen platform's builder allows it
- Pull `brand-guidelines`/`brand-developer` for brand tokens on client work
- Once `data-analyst` validates a product or business idea, **this skill is what builds the Shopify store around it** for e-commerce ventures
- Not this skill's job: custom backend/auth/admin dashboards — that's `web-app-development`; a hand-coded React marketing site — that's `build-premium-website`

## Choosing the platform

- **WordPress** — best when the client wants long-term ownership/portability of their site, content-heavy needs (blogs, resources), or deep plugin/customization requirements. Costs more technical maintenance over time.
- **Wix** — best for an all-in-one hosted solution with minimal ongoing technical overhead. Use **Wix Studio**, not the classic Editor, for any client/professional work — Studio is built for agency-grade responsive design and scales further before hitting limitations.
- **Shopify** — the default for anything that's actually a store (products, checkout, inventory) rather than a content site. Don't force e-commerce onto WordPress/Wix when Shopify's whole architecture is built for it.

## WordPress

**Default to block themes (Full Site Editing), not classic PHP themes**, for any new 2026 build. Classic themes are increasingly obsolete for new projects — block themes offer better performance, cleaner code, and give the client's own team design control without touching code afterward. Reserve classic/hybrid themes for cases needing heavy custom PHP view logic that FSE genuinely can't cover.

- **`theme.json` is the design-token layer** — colors, typography, spacing defined once here, same principle as `frontend-design`'s token system. Let it (and the block editor) handle responsive behavior; write custom media queries only for edge cases the default system doesn't cover.
- **Patterns, not theme-options panels**, are the primary way to ship design variation — build a pattern library the client can mix and match, rather than a settings page of toggles.
- **Security is defense-in-depth, not one plugin.** The biggest 2026 threat is plugin supply-chain attacks (a compromised plugin update propagates malicious code automatically) — keep the plugin count minimal, everything updated, use strong auth (passkeys/2FA over passwords alone), and maintain real backups. Every plugin added is attack surface, not a free feature.

## Wix

**Default to Wix Studio for client/professional work.** Three ways to add custom functionality via Velo, chosen by project complexity:
1. **Built-in Code Panel** — small custom interactions and CSS-level styling
2. **Wix IDE** — browser-based, VS Code-like, no local setup needed
3. **Local development** (Git integration + Wix CLI) — for serious, ongoing projects that need real version control and your own editor

Developer sovereignty is real here — every element, every line of Velo code, every design decision stays under your control, unlike more limited page builders.

## Shopify

**Online Store 2.0 (OS 2.0) is the standard** — JSON templates, sections usable on every page type (not just the homepage), dynamic section rendering for components reused across product/collection/blog pages.

- **Modern Liquid**: use array filters, `visible_if`, and LiquidDoc to keep templates clean and maintainable rather than piling up conditional logic. Delegate heavier logic to JS in a hybrid Liquid+JS approach rather than forcing everything into Liquid.
- **App discipline is the single highest-leverage lever on a Shopify store.** Every app adds JavaScript to the storefront — audit installed apps regularly, remove anything not actively used, and test the speed score after every new install. Sub-1.2-second load times convert roughly 3x better than the typical bloated 3-5 second store. When evaluating an app, prefer ones offering **app blocks** — a sign it was built to OS 2.0 standards rather than bolted on.
- **Version control everything** — Shopify Theme CLI + GitHub, branch per feature. Theme Check 2.0 (built into the CLI) catches performance, accessibility, and deprecated-pattern issues before deploy.
- **Conversion optimization means removing friction, not adding apps** — checkout simplicity, clear collection structure and navigation, and mobile usability move the needle far more than another feature app. A cluttered cart/checkout flow is one of the most common self-inflicted conversion killers.

## Critical rules

1. Never use nulled/pirated themes or plugins on any platform — the security risk (backdoors, supply-chain compromise) far outweighs any cost saved.
2. Confirm the client's long-term hosting/maintenance appetite before recommending a platform — this decision is more consequential than any individual design choice.
3. On WordPress and Shopify alike, treat every added plugin/app as a cost (performance, security, maintenance) that has to earn its place, not a free feature.
4. Don't force e-commerce architecture onto WordPress/Wix, or content-site architecture onto Shopify — pick the platform built for the actual job.
