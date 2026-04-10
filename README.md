# Text-To-SQL Agent

A Python agent that converts natural language questions into SQL queries and executes them against your database. Powered by **Claude API** (cloud) or **Ollama** (fully local — your data never leaves your machine).

---

## How it works

You ask a question in plain English. The agent:

1. Reads your database schema
2. Generates the correct SQL
3. Validates it for safety and correctness
4. Executes it
5. Returns a formatted, human-readable answer

```
You:    "Show me the top 5 products by revenue"

Agent:  | product          | total_revenue |
        |------------------|---------------|
        | Smart Watch      | 4,199.79      |
        | Mechanical Keybo | 3,119.76      |
        | Wireless Headpho | 2,879.64      |
        | Running Shoes    | 2,519.72      |
        | USB-C Hub        | 1,949.61      |

        Found 5 rows across 2 columns.
```

---

## Features

- **Natural language → SQL** — handles JOINs, aggregations, filters, date ranges
- **Two LLM providers** — use Claude API (cloud) or run fully offline with Ollama
- **Multi-database support** — SQLite, PostgreSQL, MySQL
- **Safety gates** — blocks destructive queries (DROP, DELETE, etc.) by default
- **Self-correcting** — automatically retries and fixes failed queries (up to 3 attempts)
- **Multi-turn conversations** — follow-up questions reference previous results
- **CLI + interactive REPL** — single query mode or chat-style session

---

## Project structure

```
Text-To-SQL_Agent/
│
├── main.py                   # Entry point (CLI + REPL)
├── agent.py                  # Core agentic loop
├── config.py                 # Settings loaded from .env
├── requirements.txt
├── .env.example              # Template — copy to .env and fill in
│
├── providers/                # LLM backend (swap with one env var)
│   ├── base.py               # Abstract LLMProvider interface
│   ├── claude_provider.py    # Anthropic Claude API
│   └── ollama_provider.py    # Local Ollama
│
├── skills/                   # Modular agent capabilities
│   ├── schema_introspection.py   # Reads DB schema
│   ├── query_generation.py       # SQL generation handoff
│   ├── query_validation.py       # Syntax + safety + schema checks
│   ├── query_execution.py        # Runs SQL against DB
│   ├── result_formatting.py      # Formats results for display
│   ├── error_recovery.py         # Diagnoses and fixes bad SQL
│   └── conversation_memory.py    # Multi-turn session state
│
├── db/
│   ├── connection.py             # DB connection factory
│   └── adapters/                 # SQLite / PostgreSQL / MySQL
│
├── scripts/
│   ├── seed_sample_db.py         # Create a sample database to try
│   └── benchmark.py              # Accuracy benchmark (20 queries)
│
└── tests/
    └── test_skills/              # Unit tests for skill functions
```

---

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your environment

```bash
cp .env.example .env
```

Open `.env` and set your provider:

**Option A — Claude API (cloud)**
```env
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
```

**Option B — Ollama (fully local, no API key needed)**
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:14b
```
> Make sure Ollama is running (`ollama serve`) and the model is pulled (`ollama pull qwen2.5-coder:14b`).

### 3. Set up a database

**Use the built-in sample database** (5 tables, 100 users, 300 orders):
```bash
python scripts/seed_sample_db.py
```

**Or point to your own database** — update `DATABASE_URL` in `.env`:
```env
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/mydb

# MySQL
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/mydb

# SQLite
DATABASE_URL=sqlite:///path/to/your.db
```

### 4. Run

**Single query:**
```bash
python main.py "how many users signed up last month?"
```

**Interactive REPL:**
```bash
python main.py
```

---

## Usage examples

```
You: show me the top 5 products by revenue
You: how many users are from California?
You: list orders placed in the last 30 days
You: which category has the most products?
You: show me orders with user names and product names   ← multi-table JOIN
You: now filter those to only completed orders          ← follow-up reference
You: what's the average order value per state?
```

---

## Configuration reference

All settings live in `.env`. Copy `.env.example` to get started.

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `claude` | `claude` or `ollama` |
| `ANTHROPIC_API_KEY` | — | Required when using Claude |
| `CLAUDE_MODEL` | `claude-opus-4-6` | Claude model ID |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5-coder:14b` | Local model name |
| `DATABASE_URL` | `sqlite:///db/sample.db` | SQLAlchemy connection string |
| `MAX_ROWS_RETURNED` | `100` | Hard cap on result rows |
| `MAX_ERROR_RECOVERY_ATTEMPTS` | `3` | Auto-retry limit on bad SQL |
| `ALLOW_WRITE_QUERIES` | `false` | Set `true` to allow INSERT/UPDATE/DELETE |
| `ENABLE_PROMPT_CACHING` | `true` | Claude prompt caching (reduces cost) |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Running tests

```bash
pytest tests/
```

---

## Running the benchmark

Tests accuracy across 20 standard natural language queries:

```bash
python scripts/benchmark.py
```

---

## Choosing a provider

| | Claude API | Ollama (local) |
|---|---|---|
| **Data privacy** | Sent to Anthropic | Stays on your machine |
| **SQL accuracy** | Highest | Good (model-dependent) |
| **Speed** | Fast | Depends on hardware |
| **Cost** | Per-token pricing | Free |
| **Requires internet** | Yes | No |
| **Recommended model** | `claude-opus-4-6` | `qwen2.5-coder:14b` |

Switch at any time by changing `LLM_PROVIDER` in `.env` — no code changes needed.

---

## Security

- **Write queries are blocked by default.** Only SELECT statements are allowed unless you explicitly set `ALLOW_WRITE_QUERIES=true`.
- **API keys are never committed.** The `.env` file is in `.gitignore`. Only `.env.example` (with no real values) is tracked.
- **SQL injection protection.** The validation skill checks for stacked queries and comment injection patterns before execution.
- **Row limits enforced.** Results are capped at `MAX_ROWS_RETURNED` to prevent accidental full-table dumps.

---

## Roadmap

- [x] Phase 1 — Core scaffold (CLI, providers, 7 skills, sample DB)
- [ ] Phase 2 — Schema-aware generation (FK-aware JOINs, enum value hints)
- [ ] Phase 3 — Multi-turn conversation (persistent session memory)
- [ ] Phase 4 — Validation & error recovery (self-correcting, structured logging)
- [ ] Phase 5 — REST API layer (FastAPI + `/query`, `/schema`, `/history` endpoints)

---

## License

MIT
