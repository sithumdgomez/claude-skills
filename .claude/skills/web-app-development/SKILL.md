---
name: web-app-development
description: Builds web applications with real backend logic — authentication, role-based client/admin portals, CRUD admin dashboards, and dynamic data-driven features (not static marketing content). Use when the user needs a login system, an admin panel, a client portal, a dashboard that manages real data, or any feature that requires a database and access control, not just a page of content.
argument-hint: [app/feature to build, or existing project context]
---

# Web App Development

You build the backend logic and data-driven functionality of a web application — authentication, role-based access, CRUD admin interfaces, dynamic features. This is a distinct concern from marketing-site aesthetics or Figma-stage design.

## Where this fits with the rest of the toolkit

- **`frontend-design`** owns the visual/aesthetic execution layer — call it (or hand off to it) for how screens actually look, once the data model and access rules are settled here.
- **`ui-ux-designer`** owns the Figma-stage design if a reviewable mockup is needed before code.
- **`brand-developer`/`brand-guidelines`** own brand tokens if this is client-facing and a brand identity already exists.
- **`security`** should review any auth/access-control implementation this skill produces — don't self-certify security-critical code.
- This skill owns: data model, auth, roles/permissions, admin CRUD interfaces, and dynamic data logic. Not the visual layer.

## Confirm the stack first

No fixed default — confirm framework, backend, and database before starting (e.g. Firebase/Supabase-style managed backend vs. a custom server + Postgres). The right choice depends on team size, existing infrastructure, and how much backend maintenance the user wants to own — ask rather than assume.

## Data model before UI

Define the actual entities and relationships before building any screen around them. The most common failure mode in developer-led interfaces is mirroring the underlying database structure directly into the UI instead of designing around what the user actually needs to see and do — a table schema is not a page layout.

## Auth & role-based access

- **Separate business roles from administrative roles explicitly.** Mixing them makes audits harder and mistakes more damaging — a user account and an admin privilege are not the same dimension.
- **Per-client data isolation**: authenticated users see only their own records unless explicitly granted broader access.
- **Staff vs. client separation**: internal team sees across clients; clients see only themselves.
- **MFA for elevated-privilege actions**, not just login.
- **Audit logging on all admin actions** — who did what, when, is a requirement for any real admin surface, not an afterthought.

## Admin dashboards & CRUD interfaces

This is the primary use case — get this right:
- **Clarity at a glance**: the current state of the system should be understandable within a few seconds of landing on a screen, not require hunting.
- **Real CRUD, not a content list**: searchable, filterable, sortable tables with pagination and bulk actions where the data volume warrants it.
- **Minimal cognitive load**: an admin interface is used repeatedly by someone who needs to work fast, not browse — favor density and directness over decorative polish here (that's the opposite instinct from `frontend-design`'s marketing-site guidance, deliberately).

## Dynamic data features

Build interactive features (comparison tools, filters, live search) around the actual data model defined above — not as a bolt-on with its own separate, disconnected state.

## Critical rules

1. **Data isolation must be enforced server-side.** A client-side-only check (hiding a button, filtering a list in the browser) is not real access control — anyone can bypass it. The server/database rules are the actual security boundary.
2. Never mix business and admin roles into one undifferentiated permission level.
3. Confirm the stack before writing code — don't assume a default that wasn't discussed.
4. Route the visual layer to `frontend-design`/`ui-ux-designer` rather than designing screens yourself — this skill's job is the logic underneath them.
5. Flag anything security-sensitive (auth flows, permission checks, data isolation) for a `security` skill review rather than self-certifying it.
