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
- PDF triage packets for long documents

## Star This If

- Your reading queue is full but your shipped-tool queue is empty.
- You want model announcements captured as gated candidates, not automatically trusted dependencies.
- You want claims, incidents, PDFs, and article queues turned into local state with evidence requirements.

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

## State Files

By default, the CLI writes local state under `.news-to-tools/` in the current working directory.
That directory is ignored by git.

For automation, pin the state directory so commands do not depend on the current working directory:

```bash
news-to-tools --state-dir ~/Documents/learning/news-to-tools task-list

NEWS_TO_TOOLS_STATE_DIR=~/Documents/learning/news-to-tools \
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
