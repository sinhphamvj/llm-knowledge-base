# Contributing to LLM Knowledge Base

Thanks for your interest in contributing! This project is a **template/engine** — each user forks it and fills it with their own knowledge. Contributions should improve the engine, not add personal wiki content.

---

## What to Contribute

### ✅ Welcome

- **Bug fixes** in `tools/` scripts
- **New tools** that extend the workflow (e.g., new chart types, new ingest scripts)
- **Improvements** to `AGENTS.md` or `CLAUDE.md` (better AI instructions)
- **Documentation** improvements to `README.md`
- **Workflow diagram** updates to `workflow.svg`
- **New document processing strategies** for the compile pipeline

### ❌ Do Not Include

- Personal wiki content (`wiki/concepts/`, `wiki/summaries/`, `wiki/topics/`)
- Raw source files (`raw/articles/`, `raw/papers/`, `raw/repos/`)
- Personal outputs (`outputs/reports/`, `outputs/notes/`)
- Your `.obsidian/` settings
- API keys, tokens, or `.env` files

---

## How to Contribute

### 1. Fork & Clone

```bash
git clone https://github.com/<your-username>/llm-knowledge-base.git
cd llm-knowledge-base
```

### 2. Create a Branch

```bash
git checkout -b feature/my-new-tool
```

### 3. Make Your Changes

- Follow the existing code style (Bash scripts with `set -euo pipefail`, Python 3 stdlib where possible)
- Add usage comments at the top of new scripts
- Test on macOS — this is the primary target platform (BSD grep, no GNU-only flags)

### 4. Submit a Pull Request

- Write a clear description of what your change does and why
- Reference any related issues
- Keep PRs focused — one feature or fix per PR

---

## Code Guidelines

### Shell Scripts (`tools/*.sh`)
- Start with `#!/usr/bin/env bash` and `set -euo pipefail`
- Use `ROOT="$(cd "$(dirname "$0")/.." && pwd)"` for path resolution
- Avoid GNU-only flags (e.g., use `grep -oE` not `grep -oP`)
- Include a usage comment block at the top

### Python Scripts (`tools/*.py`)
- Use Python 3 standard library where possible
- Heavy dependencies (matplotlib, networkx) should be lazy-imported with clear error messages
- Use `ROOT = Path(__file__).parent.parent` for path resolution

### Wiki Format
- All concept/summary/topic files must include YAML frontmatter with `title`, `domain`, `tags`, `created`, `updated`, `source`, `confidence`
- Use `[[wikilinks]]` for internal links (Obsidian-compatible)
- Concept files: max ~150 lines | Topic files: max ~300 lines

---

## Reporting Issues

When filing an issue, please include:
- Your OS (macOS / Linux)
- Python version (`python3 --version`)
- The exact command you ran
- The error output

---

## License

By contributing, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
