#!/usr/bin/env python3
"""
metrics.py — Token counting and cost estimation for the Knowledge Base ingest pipeline.

Model detection priority (highest → lowest):
  1. AI_MODEL env var (e.g. export AI_MODEL="claude-sonnet-4-6")
  2. CLAUDE_MODEL env var (set by Claude Code / claude CLI automatically)
  3. OPENAI_MODEL env var (set by OpenAI-compatible tools)
  4. Fuzzy match of any env var containing the model name
  5. Default: claude-sonnet-4-6

Pricing source: Anthropic API docs + Google AI Studio + OpenAI API docs, as of April 2026.
"""
import os
import sys
import json
import argparse

try:
    import tiktoken
    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False

# ---------------------------------------------------------------------------
# Pricing table — per 1M tokens (USD)
# ---------------------------------------------------------------------------
PRICING = {
    # Claude 4.6 family (current gen, April 2026)
    "claude-opus-4-6":    {"in": 5.00,  "out": 25.00, "label": "Claude Opus 4.6"},
    "claude-sonnet-4-6":  {"in": 3.00,  "out": 15.00, "label": "Claude Sonnet 4.6"},
    # Claude 4.5 family (legacy)
    "claude-opus-4-5":    {"in": 5.00,  "out": 25.00, "label": "Claude Opus 4.5"},
    "claude-sonnet-4-5":  {"in": 3.00,  "out": 15.00, "label": "Claude Sonnet 4.5"},
    # Claude 3.5 / 3 family
    "claude-3-5-sonnet":  {"in": 3.00,  "out": 15.00, "label": "Claude 3.5 Sonnet"},
    "claude-3-opus":      {"in": 15.00, "out": 75.00, "label": "Claude 3 Opus"},
    # Gemini family (Google AI pricing, April 2026)
    # Gemini 2.5 Pro: tiered — ≤200K = $1.25/$10, >200K = $2.50/$15
    # We use the standard (<200K) tier as default
    "gemini-2.5-pro":     {"in": 1.25,  "out": 10.00, "label": "Gemini 2.5 Pro"},
    "gemini-2.0-pro":     {"in": 1.25,  "out": 10.00, "label": "Gemini 2.0 Pro"},
    "gemini-1.5-pro":     {"in": 1.25,  "out": 5.00,  "label": "Gemini 1.5 Pro"},
    "gemini-1.5-flash":   {"in": 0.075, "out": 0.30,  "label": "Gemini 1.5 Flash"},
    # OpenAI — GPT-5.4 family (March 2026)
    "gpt-5.4-pro":        {"in": 30.00, "out": 180.00, "label": "GPT-5.4 Pro"},
    "gpt-5.4":            {"in": 2.50,  "out": 15.00,  "label": "GPT-5.4"},
    "gpt-5.4-mini":       {"in": 0.75,  "out": 4.50,   "label": "GPT-5.4 Mini"},
    # OpenAI — GPT-5.3 Codex (Feb 2026)
    "gpt-5.3-codex":      {"in": 1.75,  "out": 14.00,  "label": "GPT-5.3 Codex"},
    # OpenAI — GPT-5.x older
    "gpt-5.2":            {"in": 1.75,  "out": 14.00,  "label": "GPT-5.2"},
    "gpt-5":              {"in": 1.25,  "out": 10.00,  "label": "GPT-5"},
    "gpt-5-nano":         {"in": 0.05,  "out": 0.40,   "label": "GPT-5 Nano"},
    # OpenAI — o-series reasoning models
    "o3-pro":             {"in": 20.00, "out": 80.00,  "label": "o3-pro"},
    "o3":                 {"in": 2.00,  "out": 8.00,   "label": "o3"},
    "o4-mini":            {"in": 1.10,  "out": 4.40,   "label": "o4-mini"},
    # OpenAI — GPT-4 legacy
    "gpt-4o":             {"in": 2.50,  "out": 10.00,  "label": "GPT-4o"},
    "gpt-4o-mini":        {"in": 0.15,  "out": 0.60,   "label": "GPT-4o mini"},
}

# Alias map for detecting model from partial strings (user-friendly names)
ALIASES = {
    "opus-4-6":   "claude-opus-4-6",
    "sonnet-4-6": "claude-sonnet-4-6",
    "opus-4-5":   "claude-opus-4-5",
    "sonnet-4-5": "claude-sonnet-4-5",
    "opus-4":     "claude-opus-4-6",    # default latest Opus 4
    "sonnet-4":   "claude-sonnet-4-6",  # default latest Sonnet 4
    "gemini-3.1": "gemini-2.5-pro",     # "gemini 3.1" is the alias for 2.5 Pro
    "gemini-2.5": "gemini-2.5-pro",
    "gemini-2":   "gemini-2.0-pro",
    "gemini-1.5": "gemini-1.5-pro",
    # OpenAI aliases
    "gpt-5.4-pro":  "gpt-5.4-pro",
    "gpt5.4":       "gpt-5.4",
    "gpt-5.3":      "gpt-5.3-codex",
    "gpt5.3":       "gpt-5.3-codex",
    "codex":        "gpt-5.3-codex",
    "gpt5.2":       "gpt-5.2",
    "gpt5":         "gpt-5",
    "gpt4o":        "gpt-4o",
    "gpt-4o-mini":  "gpt-4o-mini",
}

DEFAULT_MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Model detection
# ---------------------------------------------------------------------------

def detect_model() -> str:
    """
    Detect the AI model in use from environment variables.
    Returns the canonical key present in PRICING.
    """
    candidates = [
        os.environ.get("AI_MODEL", ""),
        os.environ.get("CLAUDE_MODEL", ""),    # set by claude CLI
        os.environ.get("OPENAI_MODEL", ""),     # set by OpenAI-compatible tools
        os.environ.get("ANTHROPIC_MODEL", ""), # sometimes set by SDKs
        os.environ.get("GOOGLE_MODEL", ""),
    ]

    for raw in candidates:
        if not raw:
            continue
        key = _resolve_model(raw.lower().strip())
        if key:
            return key

    return DEFAULT_MODEL


def _resolve_model(raw: str) -> str | None:
    """Try to match `raw` to a known pricing key."""
    # Exact match
    if raw in PRICING:
        return raw
    # Alias match
    for alias, canonical in ALIASES.items():
        if alias in raw:
            return canonical
    # Fuzzy: check if any pricing key is a substring of raw
    for key in PRICING:
        if key in raw:
            return key
    return None


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

def count_tokens(text: str) -> int:
    if _HAS_TIKTOKEN:
        # cl100k_base is the closest approximation for both Claude & Gemini
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    else:
        # Fallback: word-count * 1.33 (reasonable for English prose)
        return int(len(text.split()) * 1.33)


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def compute_metrics(raw_file: str, model_override: str | None = None):
    if not os.path.exists(raw_file):
        print(json.dumps({"error": f"File not found: {raw_file}"}))
        sys.exit(1)

    with open(raw_file, "r", encoding="utf-8", errors="ignore") as f:
        in_text = f.read()
    in_tokens = count_tokens(in_text)

    # Infer companion summary file
    base = os.path.basename(raw_file).rsplit(".", 1)[0]
    slug = base.lower().replace(" ", "-")
    summary_file = os.path.join("wiki/summaries", slug + ".md")
    out_tokens = 0
    if os.path.exists(summary_file):
        with open(summary_file, "r", encoding="utf-8", errors="ignore") as f:
            out_tokens = count_tokens(f.read())

    # Priority: --model flag > env vars > default
    model = None
    if model_override:
        model = _resolve_model(model_override.lower().strip())
    if not model:
        model = detect_model()
    p = PRICING[model]
    cost = (in_tokens * p["in"] + out_tokens * p["out"]) / 1_000_000
    density = round(out_tokens / in_tokens, 4) if in_tokens > 0 else 0

    print(json.dumps({
        "model":      model,
        "model_label": p["label"],
        "in_tokens":  in_tokens,
        "out_tokens": out_tokens,
        "density":    density,
        "cost":       round(cost, 6),
        "tiktoken":   _HAS_TIKTOKEN,
    }))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute token & cost metrics for a compile run.")
    parser.add_argument("raw_file", help="Path to the raw input file (e.g. raw/articles/foo.md)")
    parser.add_argument("--model", help="Model name (e.g. claude-opus-4-6, gpt-5.4, o3). Overrides env detection.")
    args = parser.parse_args()
    compute_metrics(args.raw_file, model_override=args.model)
