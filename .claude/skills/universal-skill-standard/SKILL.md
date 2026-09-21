---
name: universal-skill-standard
description: The standard for what makes a Claude skill behave like a genuine domain expert rather than a smart generalist. Read and apply this whenever building a new skill or auditing/improving an existing one — it is the bar every skill is held to. Complements skill-creator (which covers the mechanics of drafting, testing, and benchmarking); this covers what "good" actually looks like and how to check for it.
argument-hint: [skill being built or audited]
---

# Universal Skill Standard

The SKILL.md file is the lever. A skill behaves like an expert not because its author is an expert, and not because the model is — but because the file encodes the *actual process and judgment a real expert follows*. This document is the bar every skill is held to.

## The core principle

Expert behavior comes from **encoding a real expert's process, not from telling the model to "be an expert."**

Research on LLM "mode collapse" shows models slide toward the most generic, most-probable output — and, critically, that *adjectival* instructions ("be an expert," "be creative," "be rigorous," "act as a senior X") do **not** escape that pull. Structural constraints and real process steps do. So the whole standard reduces to one move: **replace adjectives with structure.** Everywhere a skill says "be thorough," ask what a thorough expert actually *does*, step by step, and write that instead.

## The expert-grade rubric

Every skill should pass all ten. Each has a one-line check you can actually verify.

1. **Grounded, not generic.** Every domain claim is sourced/verified, not recalled from training memory. — *Check: could each factual claim survive a fact-check against a real source?*
2. **Structural, not adjectival.** Behavior is driven by concrete steps/constraints, not "be good at this." — *Check: search the file for "be [adjective]" — each one should be replaced by a step or a rule.*
3. **Traps encoded.** It names the specific mistakes a novice in this field makes. — *Check: is there a "common pitfalls / gotchas" section with real, field-specific traps?*
4. **The "why" is present.** Instructions explain their reasoning, not just command with capital-letter MUSTs. — *Check: does each non-obvious rule say why it matters?*
5. **Scope-honest.** It flags the limits of its own competence and escalates when real stakes exceed them. — *Check: does it say when to hand off to a licensed professional / the user / another skill?*
6. **Named frameworks with provenance.** Where a real method exists, it's named and attributed, giving the model a reasoning handle. — *Check: are methods cited ("conceptual blending, Fauconnier & Turner") rather than vaguely gestured at?*
7. **Anti-generic.** Where output could be creative, it actively fights the median (bans clichés, forces distinctiveness). — *Check: for any generative skill, is there a mechanism that blocks the obvious default?*
8. **Two-layer clarity.** Where a task splits between what the AI does and what a human does, that boundary is explicit. — *Check: does the skill ever imply it can do something it can't (render an image, sign a contract)?*
9. **Checkable behavior.** Desired behavior is stated so you could objectively verify it happened, not as vague aspiration. — *Check: could an independent tester score whether each rule was followed?*
10. **Evolves via captured failures.** The best skills start small and grow by logging real edge-case failures, not by being perfected up front. — *Check: is there a gotchas section that new failures get added to after each real use?*

## Structural mechanics checklist

Separate from the expert rubric — these are the engineering basics, and they're non-negotiable:

- **Frontmatter valid:** `name` in kebab-case matching the directory; `description` written with real trigger phrases a user would actually say (Claude tends to *under*-trigger, so lean slightly pushy). `argument-hint` present.
- **Portable paths:** reference supporting files via `${CLAUDE_SKILL_DIR}`, never a hardcoded `/Users/<someone>/...` path (that breaks the moment the skill moves or is shared).
- **Length:** under ~500 lines; push heavy detail into reference files the skill reads on demand (progressive disclosure).
- **One concern per skill:** no bundling unrelated jobs; no overlap/duplication with an existing skill; correct handoffs/cross-references to the skills that own adjacent concerns.
- **Write for a stranger:** phrase every instruction as if for a capable new hire with zero context on this task — the same standard as a good docstring for a junior developer.

## The required build / verify / debug loop

No skill is "done" from a read-through alone. The loop:

1. **Research** — ground every load-bearing claim via the `researcher` sub-skill (live sources), never from memory.
2. **Plan + approval** — present the plan and the reasoning for each addition/removal; wait for the user's go-ahead before writing.
3. **Build** — draft against the rubric above.
4. **Error-test** — run the skill on real scenarios via independent agent runs (`verify` / `webapp-testing` where applicable). Two techniques make the test trustworthy: **adversarial trap-setting** (design the scenario to bait the exact failure mode you're worried about) and **cross-domain confirmation** (test on two unrelated cases, so a fix proves it generalizes rather than passing once by luck).
5. **Fix + re-test** — apply fixes, re-run. Log anything new as a gotcha (rubric #10).

## How to use this standard

- **Building a new skill:** draft against the rubric and mechanics checklist, then run the loop.
- **Auditing an existing skill:** score it against all ten rubric items + the mechanics checklist; flag for a *deep audit* any skill whose domain facts may have gone stale (pinned tech versions, changed regulations, moved APIs); propose a plan; get approval; error-test after changes.

## The one-line test

> "Would a seasoned expert in this field recognize their *actual* working process in this file — including the mistakes they've learned to avoid — or does it read like a smart generalist's summary of the field?"

If it's the generalist's summary, it isn't done yet.
