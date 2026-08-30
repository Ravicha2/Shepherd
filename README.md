# Shepherd

Shepherd detects Architectural Decision Record (ADR) violations in Python repositories. It ingests source code and ADR documents into an Architectural Decision Graph (ADG), then uses CPT (Constraint Path Traversal) detection to find conflicts between architectural constraints and actual code. Violations are resolved through a tiered system (explicit supersession, specificity, recency, or human review).

Part of a research project at UNSW (University of New South Wales).

## Why Shepherd?

Architectural decisions decay. Teams write ADRs to record constraints like "no direct database access from handlers" or "all HTTP calls go through the gateway", but nothing checks whether the code actually follows them. Manual review misses transitive violations: a new import that indirectly violates a constraint through a chain of dependencies. Shepherd automates this by:

- **Building a graph** of your code structure and ADR constraints, not just scanning for patterns
- **Finding transitive violations** that flat LLM prompts and lint rules miss
- **Tracking violation lifecycle** so dismissed false positives stay dismissed across runs

## How It Works

1. **Seed**: Parse a repository's Python source and ADR documents, extract structural constraints via LLM, and persist an Architectural Decision Graph (ADG) in Neo4j.
2. **Detect**: Given a commit or PR diff, traverse the ADG to find constraint violations introduced by the changes.
3. **Resolve**: Violations are resolved by tier: explicit supersession, specificity, recency, then human review via dismissal.

## Prerequisites

- Docker & Docker Compose
- uv (for local dev)
- An OpenRouter API key (for LLM-based constraint extraction)

## Quick Start

```bash
# Copy env file and add your OpenRouter API key
cp .env.example .env

# Start Neo4j + API
docker compose up -d
```

- FastAPI docs: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474 (neo4j / password)

## Local Development (without Docker)

```bash
cd app
uv sync
uv run uvicorn main:app --reload
```

## Usage

All commands are run via the `cpt` CLI.

### 1. Seed a repository

Build the ADG from a repo configured in `repos/repos.yaml`:

```bash
cpt seed build --repo flask
```

This parses the source, extracts ADR constraints using an LLM, and stores the ADG in Neo4j.

### 2. Detect violations

Run CPT detection against a specific commit or PR:

```bash
# Detect at HEAD
cpt detect --repo flask

# Detect at a specific commit
cpt detect --repo flask --commit abc1234

# Detect a PR diff
cpt detect --repo flask --base main --head feature-branch

# JSON output (for scripts/CI)
cpt detect --repo flask --json
```

### 3. Manage violations

```bash
# List active violations (dismissed ones are filtered out)
cpt violation list --repo flask

# Dismiss a false positive (short_id is the 5-hex-char ID shown by `violation list`)
cpt violation dismiss <short_id> --repo flask
```

### 4. Update the ADG

When the repo changes and you need to rebuild the graph while preserving constraints and dismissals:

```bash
cpt update --repo flask --commit abc1234
```

## Repository Configuration

Repositories are defined in `repos/repos.yaml`. Each entry specifies the repo path, ADR directory, Neo4j memory settings, and ports:

```yaml
repos:
  - id: my-project
    url: ./my-project
    size: small
    adr_dir: docs/adr
    ports:
      http: 7475
      bolt: 7688
    neo4j_memory:
      heap_initial: 256m
      heap_max: 2048m
      pagecache: 512m
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `NEO4J_URI` | Neo4j Bolt URI | `bolt://neo4j:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `password` |
| `OPENROUTER_API_KEY` | API key for LLM constraint extraction | (required) |
| `LANGEXTRACT_MODEL_ID` | Model for ADR extraction | `google/gemini-3.1-flash-lite` |
| `LANGEXTRACT_MODEL_URL` | OpenRouter endpoint | `https://openrouter.ai/api/v1` |

## Tech Stack

- **Python 3.12** with FastAPI
- **Neo4j 5** for graph storage
- **Typer** CLI framework