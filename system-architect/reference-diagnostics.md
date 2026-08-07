# Root-Cause & Bottleneck Diagnostic Toolkit

Use this whenever the question is "why does this keep happening" or "why is this slow/broken/stuck" — in software, a business process, a personal routine, or a physical system. Always get a baseline measurement (Core Process Step 2) before applying any of these; without one, you're diagnosing against a guess.

**These four techniques are decades-old and stable** — fine to apply from this file directly. But if a diagnosis leans on a claim that some specific pattern is "a known failure mode" in a particular domain (e.g. a named DevOps/agile anti-pattern), verify that claim live per SKILL.md Step 5 rather than asserting it from memory.

## Choosing a technique by complexity

| Situation | Technique | Why |
|---|---|---|
| Likely single, mostly-linear cause-effect chain | **5 Whys** | Fastest (5-15 min); stop at the first fix that, if undone, makes the problem reappear |
| Multiple plausible contributing factors, unclear which matter | **Fishbone (Ishikawa)** | Forces breadth before depth — brainstorm causes across categories before picking one to chase |
| Safety-critical, or need to reason about combinations of failures | **Fault Tree Analysis** | Formal AND/OR logic from a top failure event down to combinations of sub-causes |
| The problem is a flow/throughput problem, not a single failure | **Theory of Constraints** | Identifies the one binding limiter, not just "a" cause |

Don't reach for 5 Whys on a genuinely multi-causal problem — it tends to stop at the first plausible chain and miss that two or three independent factors are compounding. Escalate technique to match complexity, per Critical Rule 5 in SKILL.md.

## 5 Whys

Start with the observed problem. Ask "why did this happen?" Take the answer and ask "why?" again. Repeat until you reach a cause that, if changed, would prevent recurrence — typically 3-5 iterations. Stop when further "why"s start explaining human nature or company culture in the abstract rather than something actually fixable; that's a sign to escalate to fishbone or reconsider the framing.

## Fishbone / Ishikawa diagram

Draw the problem as the "head." Branch into categories relevant to the domain — classic manufacturing uses People/Process/Equipment/Materials/Environment/Management, but pick categories that fit: for software, People/Process/Technology/External-dependencies works well; for a personal system, People(you)/Environment/Habits/Tools/External-obligations. Brainstorm causes under each branch before converging — the value is in forcing breadth so a plausible-but-wrong first guess doesn't get chased prematurely.

## Fault Tree Analysis

Put the failure event at the top. Branch downward into the conditions that could produce it, connected by AND gates (all sub-conditions must hold) or OR gates (any one suffices). Useful when failure requires a *combination* of conditions (e.g. "outage happens only when cache is cold AND the fallback times out") — 5 Whys tends to miss these because it follows one causal chain at a time.

## Theory of Constraints (bottleneck-finding)

Five focusing steps, applicable to any flow — a pipeline, a hiring process, a personal workload, a supply chain:

1. **Identify** the constraint — the one step/resource that limits overall throughput. Not everything that's "busy" is the constraint; the constraint is what everything else waits on.
2. **Exploit** it — get the most out of the constraint before adding capacity elsewhere (eliminate its idle time, its low-value work, its avoidable delays).
3. **Subordinate** everything else to that decision — deliberately let non-constraint parts run under capacity if that's what keeps the constraint fed and unblocked.
4. **Elevate** the constraint — only now invest in adding capacity to it (more people, better tooling, structural change).
5. **Repeat** — once resolved, the constraint moves elsewhere in the system; find the new one rather than assuming it's fixed forever.

The most common mistake is optimizing a highly visible but non-bottleneck part of the system — it feels like progress but doesn't move overall throughput at all.

## Cross-check against archetypes

If a fix has been applied before and the problem returned, check `reference-thinking.md`'s systems archetypes (fixes that fail, shifting the burden) before re-diagnosing from scratch — recurrence after a "fix" is often explained by the archetype, not by having picked the wrong root cause the first time.
