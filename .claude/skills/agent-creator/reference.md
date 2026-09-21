# Agent Creator — Reference

Authoritative reference for building Claude Code subagents. Verified against the official docs (code.claude.com/docs/en/sub-agents). If a mechanic you need isn't here, WebSearch/ WebFetch the official page or ask the `claude-code-guide` agent — subagent behavior changes between Claude Code versions, so don't rely on memory.

## 1. Where agent files live (scope + precedence)

A subagent is a single markdown file: YAML frontmatter + a system-prompt body. Location sets who can use it. When two share a `name`, the higher-priority location wins.

| Location | Scope | Priority |
|---|---|---|
| Managed settings dir | Organization-wide | 1 (highest) |
| `--agents` CLI flag (JSON, session-only) | Current session | 2 |
| `.claude/agents/` | Current project (check into VCS) | 3 |
| `~/.claude/agents/` | All your projects (personal) | 4 |
| Plugin `agents/` dir | Where plugin is enabled | 5 (lowest) |

- **Default choice for a reusable personal specialist:** `~/.claude/agents/`.
- **For a team/codebase-specific agent:** `.claude/agents/` (version-controlled).
- `name` must be unique within a scope, lowercase-hyphenated. The filename need not match `name` (identity comes from the `name` field). Directories are scanned recursively — subfolders don't change identity.
- **Restart caveat:** Claude Code watches these dirs and hot-reloads edits within seconds — **except** when you create a scope's *first* agent file in a brand-new `agents/` directory that didn't exist at session start. Then a restart is needed. Tell the user this if their new agent "isn't found."

## 2. Frontmatter fields (only `name` + `description` are required)

| Field | Req | Notes |
|---|---|---|
| `name` | ✅ | Lowercase letters + hyphens, unique. Hooks receive it as `agent_type`. |
| `description` | ✅ | **When Claude should delegate to this agent.** The whole routing mechanism. Add "use proactively" to encourage automatic delegation. |
| `tools` | — | Allowlist of tools. **Omitting = inherits ALL tools.** Comma-separated (e.g. `Read, Grep, Glob`). To preload skills, use `skills`, not `Skill` here. |
| `disallowedTools` | — | Denylist — removed from the inherited/specified set. If both set: `disallowedTools` applied first, then `tools`. A tool in both is removed. |
| `model` | — | `sonnet`, `opus`, `haiku`, `fable`, a full ID (e.g. `claude-opus-4-8`), or `inherit`. **Default: `inherit`** (main conversation's model). |
| `skills` | — | Skills to **preload** (full content injected at startup). Without it, the agent can still invoke skills via the Skill tool during execution. |
| `permissionMode` | — | `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan` (`manual` = alias for `default`, v2.1.200+). Parent `bypassPermissions`/`acceptEdits`/`auto` override it. |
| `maxTurns` | — | Cap on agentic turns before the agent stops. |
| `mcpServers` | — | Scope MCP servers to this agent (string ref to a configured server, or inline definition). Keeps their tool descriptions out of the main context. |
| `hooks` | — | Lifecycle hooks scoped to this agent (`PreToolUse`, `PostToolUse`, `Stop`→`SubagentStop`). Use for conditional rules the `tools` field can't express (e.g. allow SELECT, block INSERT). |
| `memory` | — | `user` / `project` / `local` — persistent memory dir for cross-session learning. Auto-enables Read/Write/Edit + injects `MEMORY.md`. `project` is the recommended default when used. |
| `background` | — | `true` = always run in background. Default (v2.1.198+): subagents run in background unless Claude needs the result immediately. |
| `effort` | — | `low`/`medium`/`high`/`xhigh`/`max` (model-dependent) — overrides session effort while active. |
| `isolation` | — | `worktree` = run in a temporary git worktree (isolated repo copy, auto-cleaned if no changes). |
| `color` | — | Display color: `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, `cyan`. |
| `initialPrompt` | — | Auto-submitted first user turn when the agent runs as the *main* session (`--agent`/`agent` setting). |

> Plugin subagents ignore `hooks`, `mcpServers`, and `permissionMode` for security.

## 3. Tool-availability caveats (design around these)

Some tools are **never available to a subagent even if listed in `tools`**, because they depend on the main-session UI/state:

- `AskUserQuestion` — **the agent cannot stop to ask the user a question.** Design its prompt to proceed on sensible defaults and report ambiguities back in its final message, not to interrogate.
- `EnterPlanMode`, `ExitPlanMode` (the latter works only if `permissionMode: plan`)
- `ScheduleWakeup`, `WaitForMcpServers`

Other notes:
- Subagents **inherit** internal + MCP tools by default; restrict with `tools`/`disallowedTools`.
- MCP patterns work in both fields: `mcp__<server>` or `mcp__<server>__*` grant/remove a whole server; `mcp__*` in `disallowedTools` removes all MCP tools.
- **Coordinator agents:** `tools: Agent(worker, researcher)` restricts which subagent *types* it may spawn. `Agent` alone = spawn any. Omit `Agent` = can't spawn subagents. (The `Agent(type)` allowlist only applies when the agent runs as the main thread via `--agent`.)
- A subagent gets **only its own system prompt + basic env details**, not Claude Code's full system prompt. It does **not** see the main conversation's history, prior skills, or already-read files (a `fork` is the exception — it inherits everything).

## 4. Model selection — right-size it

Cost lever. Don't default to Opus.

| Job shape | Model |
|---|---|
| Grep/read-heavy exploration, mechanical search | `haiku` |
| Balanced review, most specialist work | `sonnet` |
| Deep reasoning, nuanced review, hard builds | `opus` |
| Most demanding long-horizon/agentic work | `fable` |
| Genuinely needs whatever the session runs | `inherit` (default) |

## 5. Starter template

```markdown
---
name: <lowercase-hyphenated-name>
description: <what it does + when to delegate to it; concrete triggers; "use proactively" if it should auto-run>. Use when <situations>. Do NOT use for <adjacent things that belong elsewhere>.
tools: Read, Grep, Glob        # least privilege; add Bash/Write/Edit only if the job needs them
model: sonnet                  # right-size: haiku / sonnet / opus / fable / inherit
# skills: [some-skill]         # optional: preload a skill the job leans on
---

You are a <role> specializing in <domain>.

When invoked:
1. <first concrete step>
2. <next step>
3. <produce the deliverable>

<Guardrails — restate the not-touch rules: e.g. "You have read-only access. If asked to
modify files, explain that you can't and report what you'd change instead.">

Output format:
- <exactly what to return, and how — the agent's result is all the parent sees>

<If the job maps to a skill, tell it to use that skill rather than re-deriving its knowledge.>
```

(Write the real body via the `prompt-engineer` skill — the template just shows the shape.)

## 6. Error-testing rubric

Agents are non-deterministic — grade **behavior tendencies**, and let the human make the final call. Run 2–3 tasks (representative + adversarial) and check:

| Dimension | Pass looks like | Failure → fix |
|---|---|---|
| **Triggers correctly** | A matching request routes to the agent | Undertriggers → sharpen/broaden the `description` with real phrasings |
| **Rejects near-misses** | A task that belongs elsewhere does NOT get grabbed | Overtriggers → tighten `description`, add a "do NOT use for…" clause |
| **Stays in its lane** | A read-only agent asked to modify explains it can't, doesn't write | Lane violation → remove the tool (`tools`/`disallowedTools`) AND restate the guardrail in the prompt |
| **Tool discipline** | Only uses granted tools; a missing tool surfaces as a limit | Reaching for ungranted tools → confirm the allowlist; add a needed tool only if the test proves it |
| **Right output** | Result kind/format/depth matches the job | Wrong output → refine the system prompt (via `prompt-engineer`) |

**Adversarial probes worth running:** ask a read-only agent to make a change; give it a task just outside its scope; hand it an ambiguous request (it should proceed on a stated default or report back — it *can't* ask you, per §3).

## 7. Common failure modes

- **Over-broad tools** — omitting `tools` inherits everything; a "reviewer" that can `Write`/`Bash` isn't a reviewer. Grant explicitly.
- **Vague description** — the agent never gets delegated to. This is the most common real-world failure.
- **Over-delegation by whoever uses the agent** — subagents start fresh and re-derive context (cold, not free). They're for verbose/isolated/repeatable jobs, not one-file reads the main thread should just do. Note this for the user.
- **Asking-the-user prompts** — an agent that says "I'll ask the user which option…" will stall; it has no `AskUserQuestion`. Design for defaults + report-back.
- **Building an agent when a skill fits** — if it's reusable knowledge for the main thread, it's a `skill-creator` job.
