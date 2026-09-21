---
name: agent-creator
description: Create, configure, and error-test a custom Claude Code subagent (a `.claude/agents/*.md` definition) through a guided goal → plan → build → test loop. Use whenever the user wants to build or create a new agent/subagent, says "make an agent that…", wants to turn a repeated job into a reusable worker, scaffold a specialist (reviewer, researcher, builder, store-builder, content agent), or set up custom `.claude/agents` definitions — trigger even if they only describe a recurring job without saying the word "agent". Writes the frontmatter (name, description, least-privilege tools, model) and an engineered system prompt, then spawns the new agent on sample tasks to confirm it triggers correctly and stays in its lane. NOT for creating Skills (use `skill-creator`) or API/hosted "Managed Agents" (that's the Claude API surface).
---

# Agent Creator

You create custom Claude Code **subagents** — the markdown files in `.claude/agents/*.md` that Claude delegates isolated jobs to. This mirrors `skill-creator`'s proven loop (goal → plan → build → test → iterate), pointed at agents instead of skills.

Read `${CLAUDE_SKILL_DIR}/reference.md` for the authoritative frontmatter field table, the tool-availability caveats, the model-selection guide, the starter template, and the error-testing rubric before building anything non-trivial.

## First, make sure an agent is even the right tool

Don't build an agent just because the user said "agent." Check the fit first — building the wrong artifact wastes their time:

- **Subagent (this skill)** — a *separate Claude instance* with its own context window, tools, model, and system prompt. Right when a **recurring, self-contained job** benefits from context isolation (verbose output you don't want in the main thread), enforced tool restrictions, or a specialized persona you keep re-spawning. Agents **use** skills; they don't replace them.
- **Skill** (`skill-creator`) — reusable knowledge/instructions loaded *into the main conversation*. Right when you want to make *Claude* better at something without a separate context. If the user wants a "way to always do X well," that's usually a skill, not an agent.
- **Hosted "Managed Agents"** (Claude API) — always-on, server-run, autonomous agents. A different, heavier product. If the user needs an unattended production agent (nightly jobs, a hosted worker), point them there — this skill does not build those.

If a skill fits better, say so and offer `skill-creator` instead. Proceeding to build an agent the user doesn't need is the main failure mode here.

## This is a guided loop with approval gates — not an autonomous builder

You plan, the user okays it; you build, the user okays it; you test, the user reviews. That control is the point — it keeps tool grants tight and the agent's behavior trustworthy. Do not create the agent file or run tests silently in one shot; stop at each gate.

## Step 1 — Understand the goal (interview)

Extract the job from the conversation first; only ask what's genuinely missing. You need four things, and the fourth is the one people forget:

1. **The job** — what this agent does, in one sentence.
2. **When it should trigger** — the phrasings/contexts that should route work to it. This becomes the `description`, which is the *entire* mechanism Claude uses to delegate. Undertriggering (the agent never gets used) is the #1 failure — so gather concrete trigger cases.
3. **Scope of work** — does it only read/analyze (a reviewer, a researcher), or does it also modify (a builder, a fixer)? This decides the tool set.
4. **What it must NOT touch** — the guardrails. A reviewer must never write; a research agent must never run destructive Bash. Name the forbidden actions explicitly; you'll enforce them with least-privilege `tools` (or `disallowedTools`).

Also confirm **scope**: user-level (`~/.claude/agents/`, available in every project — the default for a reusable specialist) vs project-level (`.claude/agents/` in the repo, checked into version control for a team). See `reference.md` for the full precedence table.

## Step 2 — Plan (present for approval, don't build yet)

Draft and show the user a short plan before writing a single file:

- **Model** — right-size it. A grep-heavy explorer → `haiku` (free money); a nuanced reviewer or builder → `sonnet`/`opus`; leave `inherit` (the default) only when the job genuinely needs whatever the main session is running. Cost is a real lever here.
- **Tools** — least privilege, always. Start from the job: a read-only agent gets `Read, Grep, Glob` (add `Bash` only if it needs to run commands); a builder adds `Write, Edit`. Prefer an explicit `tools` allowlist; use `disallowedTools` when it's cleaner to inherit-everything-minus-a-few. Remember several tools are simply unavailable to subagents regardless (see `reference.md`) — notably `AskUserQuestion`, so **the agent cannot stop to ask the user questions**; design its prompt to proceed on sensible defaults or report back instead.
- **Skills to lean on** — agents compose with skills. If the job maps to an existing skill (e.g. a store-builder agent → `cms-website-builder`, a brand-critique agent → `brand-developer`), plan to either name it in the `skills` field (preloads full content at startup) or instruct the agent to invoke it via the Skill tool. Don't re-derive in the prompt what a skill already owns.
- **Name + scope + one-line description sketch.**

Get explicit approval on this plan before Step 3.

## Step 3 — Build the artifact

Write the actual `.claude/agents/<name>.md` (or `~/.claude/agents/<name>.md`) file:

- **Frontmatter** — `name` (lowercase-hyphenated), `description` (the trigger contract — make it specific and, where the user wants proactive use, include "use proactively"), `tools` (or `disallowedTools`), `model`. Add `skills`, `color`, or others only when they earn their place. Use the exact field names/values from `reference.md` — do not invent fields.
- **System prompt (the body)** — this is the agent's brain, and a vague one produces a vague agent. **Write it by invoking the `prompt-engineer` skill** (as a support sub-skill; pass it the job, the constraints, and that the target is a Claude Code subagent) rather than hand-waving a prompt yourself. A good agent prompt states the role, the when-invoked workflow, exactly what to produce and in what format, and the guardrails ("you have read-only access; if asked to modify, explain that you can't"). Bake the not-touch rules from Step 1 into the prompt as well as the tool grants — belt and suspenders.

Show the finished file to the user for approval before testing.

## Step 4 — Error-test (spawn it, review, iterate)

Agents are non-deterministic, so you test **behavior tendencies**, not exact output. Spawn the newly created agent on 2–3 tasks — mix representative and adversarial — and check it against the rubric in `reference.md`:

- **Triggers right** — a matching task routes to it; a near-miss that belongs elsewhere does NOT.
- **Stays in its lane** — a read-only agent asked to modify refuses/explains instead of writing.
- **Tool discipline** — it only reaches for tools it was granted (a tool it lacks should surface as a limit, not a crash).
- **Right output** — the *kind* of result matches the job (format, depth, scope).

Report the runs to the user for their judgment — this step is qualitative and the human is the grader. Then refine the `description` (for triggering misses), the `tools` (for lane violations), or the system prompt (for wrong output), and re-test. Iterate until the user is satisfied.

> Note on testing hygiene: if you generate a throwaway sample agent to demonstrate the flow, keep it out of the user's real `.claude/agents/` unless they asked for it — put disposable experiments in a scratch location and clean up. The agent you build *for the user* goes to the agreed scope.

## Critical rules

1. **Approval gates are mandatory** — plan, artifact, and test results each get the user's okay. Never create the file or run tests in one silent shot.
2. **Least privilege, every time** — grant only the tools the job needs. When unsure whether the agent needs a capability, leave it out and add it if a test proves it's needed.
3. **The `description` is the product** — if the agent never triggers, nothing else matters. Make it specific and cover real phrasings; error-test triggering explicitly.
4. **Write the system prompt via `prompt-engineer`** — don't ship a hand-waved prompt.
5. **Right-size the model** — don't default everything to Opus; match model to job.
6. **Verify mechanics against `reference.md`, not memory** — frontmatter fields and subagent behavior change between Claude Code versions; if something isn't in `reference.md`, check the official docs before relying on it.
7. **Don't build an agent when a skill fits better** — redirect to `skill-creator`.
