# Software / IT / Enterprise Architecture Toolkit

Use this when the system in question is software, infrastructure, or a technical product. This is the domain where formal architecture practice is most mature — borrow its rigor even when working in other domains via `reference-domains.md`.

**The concepts below (quality attributes, C4, ADRs, the pattern list) are a starting layer, not frozen truth.** They're stable enough to reason from, but if a real recommendation leans on a specific named pattern or "current best practice" claim, verify it live per SKILL.md Step 5 before presenting it as proven — this file was written once and doesn't update itself.

## Quality attributes (the trade-off vocabulary)

Before designing structure, name and rank the quality attributes (a.k.a. non-functional requirements) this system needs, because they trade off against each other and the ranking is the design decision:

- **Scalability** — how it behaves as load grows (users, data volume, request rate).
- **Reliability/availability** — how it behaves under partial failure; what "acceptable downtime" means here.
- **Security** — what's being protected, from whom, and what the acceptable residual risk is.
- **Maintainability** — how easily this can be understood and changed by people who didn't build it.
- **Performance** — latency/throughput targets, and for whom (p50 vs p99 matters).
- **Cost** — build cost, run cost, and the cost of the team's time to operate it.

Two systems with identical functional requirements get different architectures once these are ranked differently — e.g. a startup MVP optimizes for maintainability/cost over scalability; a payments system inverts that. State the ranking explicitly rather than leaving it implicit — that's usually where architecture disagreements actually live.

## The C4 model (documenting the "what")

Four nested levels, each for a different audience — don't try to produce all four for everything; levels 1-2 are almost always worth it, 3-4 only for genuinely complex or high-churn components:

1. **Context** — the system as one box, its users, and the other systems it talks to. Aligns stakeholders on scope.
2. **Container** — the deployable/runnable units inside it (services, databases, apps, queues) and how they talk to each other. Aligns architects on structure.
3. **Component** — inside one container, the major structural building blocks and their responsibilities. Aligns developers on internal design.
4. **Code** — class/module-level detail, generated from code rather than hand-maintained, if used at all.

## Architecture Decision Records (documenting the "why")

An ADR is a short, durable record of one significant decision. Minimal structure:

```
# ADR-NNN: <short decision title>

## Context
What situation/problem/constraint made a decision necessary.

## Decision
What was decided, stated as a clear declarative sentence.

## Alternatives considered
What else was on the table, and why it was rejected.

## Consequences
What this makes easier, what it makes harder, and any new risks introduced.

## Revisit when
The condition that should trigger reconsidering this decision (e.g. "if traffic exceeds 10x current", "if the vendor deprecates X", "in 12 months regardless").
```

Write one ADR per significant decision, not one giant document for the whole system. C4 diagrams show what the architecture looks like; ADRs show why — keep both, they're not redundant.

## Common architecture patterns (starting points, not a checklist)

- **Layered/monolith** — simplest to build, deploy, and reason about; the right default until there's a specific reason to fragment it. Weak at independent scaling/deployment of parts.
- **Microservices** — independent scaling, deployment, and team ownership per service; costly in operational complexity, network reliability, and distributed-debugging burden. Justify with an actual scaling or team-topology need, not novelty.
- **Event-driven** — good for decoupling producers from consumers and for systems with bursty or asynchronous workloads; costly in traceability and eventual-consistency reasoning.
- **Modular monolith** — a middle ground: internal modularity/boundaries enforced in code, single deployable unit. Often the right choice for teams too small to absorb microservices' operational tax.

Pick the simplest pattern that satisfies the ranked quality attributes from above — complexity should be justified by a specific requirement, not added preemptively "for scale we might need later."

## Trade-off analysis (lightweight ATAM)

For any non-trivial architecture decision: list the quality attributes in tension, state which one wins and why given the constraints from Core Process Step 1, and name what's given up. This three-line exercise, done explicitly, prevents most architecture disagreements that are actually just unstated differing priorities.
