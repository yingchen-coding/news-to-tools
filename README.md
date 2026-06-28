# News to Tools

[![CI](https://github.com/yingchen-coding/news-to-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/yingchen-coding/news-to-tools/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Stop hoarding AI news. Turn the useful parts into tasks, gates, and local tools.

Most AI/news feeds are noise: model hype, screenshots, benchmark claims, safety incidents, and
workflow ideas. News to Tools converts the parts worth acting on into concrete local state:

- workboard tasks with acceptance criteria and evidence
- guarded model candidates with `auto_route_allowed=false` until verified
- usage/quota budgets for long-running agents
- medical AI claim gates that block clinical use without independent validation
- model security incident logs
- AI claim diligence for benchmark, cost, safety, deployment, adoption, and physical-AI claims
- PDF triage packets for long documents
- design handoff packets that turn product notes into component tasks and acceptance criteria

## Star This If

- Your reading queue is full but your shipped-tool queue is empty.
- You want model announcements captured as gated candidates, not automatically trusted dependencies.
- You want claims, incidents, PDFs, and article queues turned into local state with evidence requirements.
- You want a public, generic way to turn impressive AI claims into "implement", "track",
  "verify-first", or "reject" decisions.

## Install

```bash
python -m pip install -e .
```

If your shell has not picked up the console-script path, use:

```bash
python -m news_to_tools --help
```

## Quick Demos

Add an article-derived implementation task:

```bash
news-to-tools task-add "Implement article: desktop agent scheduler" \
  --source "AI newsletter" \
  --source-url "https://example.com/article"

news-to-tools task-list
```

Import a generic queue JSON into the workboard:

```bash
news-to-tools queue-import examples/queue.sample.json
news-to-tools task-list
```

By default, `queue-import` imports items with missing/new/queued/todo/pending status and skips
`done` or `dropped` items. Use repeated `--include-status STATUS` flags when your queue uses custom
status names.

Queue import is idempotent. Re-running the same feed will not duplicate tasks; matching uses
`source_url` when present and falls back to the generated task title. Article priority and evidence
fields such as `summary`, `notes`, and source links are carried into the workboard.

Register a hyped model without letting your automation route to it:

```bash
news-to-tools model-add "example/SubQ-SSA" \
  --source-url "https://example.com/model" \
  --requirement independent_benchmark \
  --notes "Claims are unverified; do not route production tasks."
```

Block a medical AI claim until it has independent validation:

```bash
news-to-tools medical-claim "Model claims 91% doctor adoption" \
  --source-url "https://example.com/medical-ai" \
  --text "Claims 91% doctor adoption for medical record generation."
```

Gate a broad AI claim before you build from it:

```bash
news-to-tools claim-add \
  --subject "Example coding model" \
  --domain coding \
  --claim-type benchmark \
  --claim "Solves more repository issues on a public benchmark." \
  --source-url "https://example.com/coding-model" \
  --benchmark "Public issue-resolution benchmark" \
  --reproduction-evidence "local harness passed" \
  --status validated

news-to-tools claim-list
news-to-tools claim-validate
```

High-risk claims are intentionally stricter. Medical, security, and physical-AI deployment claims
need safety or reproduction evidence before they can move past `verify-first`.

Turn a design or product brief into buildable UI tasks:

```bash
printf "Search by zipcode and filter by price.\nExport selected results as a table.\n" > brief.txt

news-to-tools design-handoff brief.txt --add-to-workboard
news-to-tools task-list
```

The command writes a local `handoff.json` and `handoff.md` under `.news-to-tools/design-handoffs/`.
Each inferred component includes default/loading/empty/error states and acceptance criteria, then
can be imported into the workboard without duplicating tasks on rerun.

## State Files

By default, the CLI writes local state under `.news-to-tools/` in the current working directory.
That directory is ignored by git.

For automation, pin the state directory so commands do not depend on the current working directory:

```bash
news-to-tools --state-dir ./.news-to-tools-state task-list

NEWS_TO_TOOLS_STATE_DIR=./.news-to-tools-state \
  news-to-tools task-add "Implement article: agent trace action extraction"
```

## Local Review Check

Before pushing changes, run:

```bash
scripts/pr_review_check.sh
```

## What This Is Not

This is not a scraper for private chats. The public repo intentionally excludes personal WeChat
state, screenshots, and private queues. Bring your own article feed or queue fixture.

This is not a benchmark system. Model candidates are blocked from automatic routing until you record
real local verification.

This is not medical advice. Medical AI claims are recorded as claims and blocked by default.
