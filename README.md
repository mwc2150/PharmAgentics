# PharmAgentics

Multi-agent AI platform for pharma commercial analytics, where a shared data layer and orchestration power two agents: weekly brand-performance briefings and plain-language forecast explanations.

The initial data foundation loads 14 supplied synthetic datasets into a persistent
DuckDB database. It preserves missing and duplicate feed artifacts, reports their
evidence, and provides weekly Rx KPIs gated by feed health. Gemini integration
and analytical agent tools are future work.

See [DuckDB first-run instructions](docs/DUCKDB_FIRST_RUN.md) for installation,
data checks, example queries, and tests. Python 3.11+ is required.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run
`uv sync` in the repository root. It installs Python 3.12 if needed and every
dependency pinned in `uv.lock`, the same on Windows, macOS and Linux. Run commands
through uv, for example `uv run python -m unittest discover -s tests -v`.
