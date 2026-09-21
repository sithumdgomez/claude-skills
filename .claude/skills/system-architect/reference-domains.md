# Domain Adaptation Notes

The method in `reference-thinking.md` and the Core Process in `SKILL.md` is the same across every domain below — these notes exist only to translate vocabulary and point at what "elements," "flows," "constraints," and "trade-offs" typically look like in each. Don't invent a parallel method per domain; reuse the one method.

**Named patterns mentioned below (e.g. a specific agile ceremony, a named org-design model) are starting hints, not verified facts.** If one becomes load-bearing for an actual recommendation, check it live per SKILL.md Step 5 first.

## Business / organizational systems

- **Elements**: teams, roles, decision rights, tools, budget pools.
- **Interconnections**: reporting lines, handoffs between teams/stages, approval workflows, information flows (who sees what metric, and when).
- **Stocks/flows**: backlog size, headcount, cash runway, customer trust/NPS, inventory.
- **Common trade-offs**: speed vs. quality, autonomy vs. consistency, centralization vs. local ownership, short-term revenue vs. long-term capability.
- **Common constraints**: budget, hiring pipeline/skill availability, regulatory/compliance obligations, existing tooling/vendor lock-in, org politics (a real constraint even though it's not written down anywhere).
- **Typical bottleneck locations**: a single approver, a shared platform team, a decision that requires a meeting that only happens monthly.
- **Documentation equivalent of an ADR**: a decision memo — context, decision, alternatives considered, consequences, and when to revisit (e.g., "reconsider this org structure at 2x headcount").

## Personal / life systems

- **Elements**: you, your environment, your tools/habits, the people you routinely interact with.
- **Interconnections**: habit loops (cue → routine → reward), calendar/time allocation, physical environment layout, information inputs (what you consume, and when).
- **Stocks/flows**: energy/willpower, accumulated skill, to-do backlog, savings, relationship trust.
- **Common trade-offs**: structure vs. flexibility, short-term comfort vs. long-term goal progress, breadth vs. depth of commitments.
- **Common constraints**: time, energy, existing obligations, sunk cost in current routines/tools.
- **Feedback loops worth naming explicitly**: a reinforcing loop where skipping a habit once makes it easier to skip again (a "shifting the burden" pattern — the short-term relief of skipping erodes the long-term system); a balancing loop like a fixed weekly review that catches drift before it compounds.
- **Leverage points that matter most here**: environment/structure (level 3, e.g. removing friction or adding it deliberately) and rules (level 8, e.g. a personal policy like "no phone at the desk") tend to outperform willpower-level parameter tweaks ("try harder") — this maps directly onto Meadows' ranking.
- **Documentation equivalent of an ADR**: a short written note on why a routine/system was set up a certain way, so a future change to it is deliberate rather than accidental drift.

## Physical / mechanical systems

- **Elements**: components, materials, energy sources, control mechanisms.
- **Interconnections**: physical linkages, energy/material flow paths, control signals.
- **Stocks/flows**: literal — temperature, pressure, charge, fuel, material inventory.
- **Feedback loops are often literal control systems**: a thermostat is a textbook balancing loop (senses deviation from setpoint, acts to correct it); runaway heating/vibration is a textbook reinforcing loop.
- **Common trade-offs**: efficiency vs. redundancy/safety margin, cost vs. durability, simplicity of maintenance vs. peak performance.
- **Common constraints**: physical/material limits, safety and regulatory standards, energy budget.
- **Diagnostics**: fault tree analysis originated in exactly this domain (aerospace, nuclear) — reach for it first here over 5 Whys when failure could involve component combinations.

## When a system spans domains

Most real systems aren't purely one domain — a "we keep missing deadlines" problem is usually a business-process system with a personal-habit system nested inside it, sitting on top of a software system's actual throughput limits. When that happens, map each layer's elements/flows separately, find each layer's own bottleneck, and be explicit about which layer the chosen intervention targets — a fix aimed at the wrong layer (e.g., a process change when the real constraint is a person's energy) won't hold.
