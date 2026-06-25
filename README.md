# News to Tools

Turn AI/news articles into an implementation backlog with evidence gates, not another summary.

Most AI news is noise: model hype, screenshots, benchmark claims, safety incidents, and workflow
ideas. This CLI converts those items into concrete local state:

- workboard tasks with acceptance criteria and evidence
- guarded model candidates with `auto_route_allowed=false` until verified
- usage/quota budgets for long-running agents
- medical AI claim gates that block clinical use without independent validation
- model security incident logs
- PDF triage packets for long documents

## Install

```bash
python -m pip install -e .
```

## Quick Demos

Add an article-derived implementation task:

```bash
news-to-tools task-add "Implement article: desktop agent scheduler" \
  --source "AI newsletter" \
  --source-url "https://example.com/article"

news-to-tools task-list
```

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

## What This Is Not

This is not a scraper for private chats. The public repo intentionally excludes personal WeChat
state, screenshots, and private queues. Bring your own article feed or queue fixture.

This is not a benchmark system. Model candidates are blocked from automatic routing until you record
real local verification.

This is not medical advice. Medical AI claims are recorded as claims and blocked by default.

