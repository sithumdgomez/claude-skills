# General Systems Thinking (Domain-Agnostic Layer)

This is the universal method underneath every domain-specific reference file. It comes from Donella Meadows' systems theory (*Thinking in Systems: A Primer*) and Peter Senge's systems archetypes (*The Fifth Discipline*), and it applies unchanged whether the system is code, a company, a household, or a machine.

## What a system is

A system is a set of **elements**, **interconnected**, organized to serve some **purpose or function**. Change any one of those three and behavior changes:
- Elements are the parts — components, people, teams, habits, machine parts.
- Interconnections are the relationships and flows between elements — data flow, reporting lines, handoffs, cause-effect links, physical linkages.
- Purpose/function is often the least visible but most powerful of the three — it's frequently not what's officially stated, but what the system's actual behavior reveals it to be optimizing for.

## Stocks and flows

A **stock** is an accumulated quantity — a backlog, a bank balance, inventory, trust, skill level, water in a tank. A **flow** increases or decreases a stock — inflows and outflows. Most "why is this stuck" questions are really "what's the stock, and what's throttling its inflow or outflow." Naming the actual stock in play (not just the visible symptom) is often the single most clarifying move in a systems conversation.

## Feedback loops

- **Balancing (negative) loops** stabilize a system toward a goal — a thermostat, a deadline that forces prioritization, a budget cap. They resist change, which is often desirable (stability) and sometimes the very thing blocking a needed change.
- **Reinforcing (positive) loops** amplify — success breeding success, a debt spiral, a bug that causes churn that causes fewer tests that causes more bugs. Reinforcing loops explain runaway growth and runaway decline alike.
- The relative *strength* of a balancing loop against whatever it's correcting for is itself a common leverage point — a weak balancing loop (e.g., a code-review process too weak to catch real problems) lets a reinforcing loop run unchecked.

## Leverage points (Meadows, shallow → deep)

Ranked roughly from least to most effective place to intervene. Lower-numbered points are easier to pull but tend to need constant re-pulling; higher-numbered points are harder to shift but tend to fix things at the source:

1. **Constants, parameters, numbers** — budgets, thresholds, quotas. Easy to change, usually the weakest lever.
2. **Buffers** — the size of stabilizing stocks relative to their flows (savings, slack time, inventory).
3. **Structure of stocks and flows** — the physical or organizational network itself (org chart, pipeline topology, room layout).
4. **Delays** — how quickly the system perceives and reacts to change relative to how fast the system itself changes.
5. **Balancing feedback loops** — the strength of the loops correcting deviation (review processes, QA, checks and balances).
6. **Reinforcing feedback loops** — the strength of loops driving growth or decline; slowing a harmful reinforcing loop is often higher leverage than strengthening a balancing one.
7. **Information flows** — who has access to what information, and when (visibility into a metric often changes behavior more than a rule about the metric).
8. **Rules** — incentives, constraints, punishments — the actual rules of the game, not the stated ones.
9. **Self-organization** — the system's power to add, remove, or evolve its own structure (a team's ability to change its own process; a codebase's ability to be refactored).
10. **Goals** — the purpose the system is actually organized around, which is often not the stated mission.
11. **Paradigm** — the shared, usually unstated, assumptions that the goals, rules, and structure all derive from.
12. **Transcending paradigms** — holding the whole worldview as one option among many rather than fixed truth; rarely needed but occasionally the only real fix.

Practical use: when someone proposes fix at level 1-2 (tweak a number) for a problem that's actually structural (level 3+), name that gap explicitly — it explains why the same problem keeps recurring after "fixing" it.

## Systems archetypes (recurring dysfunctional patterns)

These are recognizable causal-loop patterns that show up across every domain. Naming which one is in play often does more diagnostic work than any amount of new analysis.

- **Fixes that fail**: a quick fix resolves the symptom immediately but creates an unintended consequence, with a delay, that reintroduces or worsens the original problem. (E.g., hiring contractors to hit a deadline, which erodes team knowledge and slows the *next* deadline.)
- **Shifting the burden**: a symptomatic fix relieves the immediate pain, which reduces the pressure to pursue the harder fundamental fix, which — over time — atrophies the system's capacity to ever apply the fundamental fix. (E.g., relying on a workaround so long that no one remembers how or has the standing to fix the real cause.)
- **Tragedy of the commons**: multiple actors share a common resource and individually benefit from consuming more of it, while the cost of depletion is shared — so no individual actor is incentivized to hold back. (E.g., shared infra, shared attention/meeting time, a shared budget pool.)

If a proposed fix looks like it's relieving a symptom rather than the underlying constraint, say so explicitly and name which archetype it resembles — that's more useful to the person than silently implementing it.
