# Model choice, sessions and tokens

The principle: spend expensive reasoning only where a mistake would repeat, and let scripts
do everything that has one right answer.

## Which model for which work

| Work | Model | Effort | Why |
|---|---|---|---|
| Session 1 design: CLAUDE.md, the category list, anything that sets up the whole job | Opus | high | Done once, and a mistake here repeats on every row |
| Writing and fixing parsers and scripts | Sonnet | medium | Strong at code, much cheaper, and the balance check tells it when it's wrong |
| A statement still failing after 2 Sonnet attempts; odd matching cases | Opus | high | Worth paying for the hardest 5% |
| Payee rules | Sonnet | medium (low for obvious shops) | Judgement inside a fixed category list |
| Clean names, grouping name variants, normalise.csv tweaks | Haiku | low | Mechanical, and the original description is always kept |
| Final accountant's-eye review | Opus | high | Spotting what's *missing* needs the best reasoning, and the input is small (summaries only) |
| Balance checks, matching, applying rules, totals, workbooks | Python | – | Always gives the same result, costs nothing to re-run, and is the only thing that touches amounts |

**Why not Haiku for classification?** After grouping there are only about 1,000 payees, so
the saving is small, and one wrong call repeats on every row for that payee.

**Setting it:**
- Claude Code: `claude --model sonnet --effort medium`, or `/model` inside a session.
- Subagents: `model: sonnet` in the agent file.
- Claude.ai: turn extended thinking on for Opus design and review work; leave it off for the
  rest.

## Sessions

| Start fresh (`/clear` or restart) when… | Continue the same session when… |
|---|---|
| A step's check has passed | You're in the middle of a step, fixing what its check found |
| You're moving to a different phase or bank | Context is under about half full (`/context` shows it) |
| Context is over about 60% full | |
| You're switching models (Opus design → Sonnet scripting) | |

- **End every session with:** "Update PROGRESS.md (status, numbers, next step) and
  DECISIONS.md." Then clear the context.
- **Don't rely on `/compact` here.** A summary can drop "S041 page 3 has a reversed row".
- **`claude --continue`** only to resume a step that was interrupted part-way.
- **Opening line for every new session:** "Read PROGRESS.md and do the next step."

What lives where, so a new session never has to re-read everything:
- `CLAUDE.md` loads automatically. It holds the rules, the folder map, the commands and who
  decides what. Keep it under about 150 lines.
- `PROGRESS.md` holds the checklist, current numbers (e.g. "95/97 balanced; S041, S077
  failing – why") and the exact next step.
- `DECISIONS.md` holds the owner's judgement calls, dated.
- `config/*.csv` is the machine-readable memory (rules, people, decisions). Read only the
  one the step needs, with offset/limit.

## When to use parallel agents

| Work | Parallel? | Why |
|---|---|---|
| Bank parsers | **Yes:** one `bank-parser` subagent per bank, after Session 1 fixes the columns | Independent work, each needs its own layout context, and each verifies itself against the balance check |
| Payee rules | **No:** one session, in batches, unless there are more than about 2,000 payees | Consistency matters more than speed; parallel agents label similar payees differently. If you do split, run `classify.py` and check `review/rule_conflicts.csv` |
| Matching, reconciliation, totals | No | Scripts. There's nothing for an agent to decide |
| Review | No | The owner does it |
| Final review | No | It needs one reviewer who sees the whole picture |

Each subagent starts cold and re-reads its context, so only split work that is large and
independent.

## The biggest token wasters, and the fix for each

| Waster | Fix |
|---|---|
| Claude reading PDFs: thousands of tokens a page × 97 files × every retry | Scripts extract; Claude sees one masked sample per layout (`dump_sample.py`) |
| Classifying row by row | Classify payees once, and `classify.py` applies the rules to every row |
| Claude writing the ledger in replies | Claude edits scripts and rules, and scripts write the files. Output tokens cost the most, and retyped numbers break rule 1 |
| Scripts that print whole tables | Every pipeline script prints a summary and writes the details to a file |
| Reading whole CSVs | Read with offset/limit, or `grep` for the statement or txn_id you need |
| One marathon session | One step per session, handed over through PROGRESS.md |
| Re-explaining the project | CLAUDE.md loads automatically |
| Opus, or high effort, on routine code | Follow the table above |
| Re-classifying everything after one change | `payees.py` marks only payees with no rule as `new` |
| Subagents for small jobs | Use them only for the parsers, and for the payee rules only when very large |
| Debugging extraction by eye | `reconcile.py` names the exact bad row in `review/reconcile_row_errors.csv` |
