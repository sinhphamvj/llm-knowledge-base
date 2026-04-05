---
title: "Transformer Architecture"
domain: ai
tags: [architecture, attention, deep-learning, nlp]
created: 2017-06-12
updated: 2025-01-01
source: "raw/papers/attention-is-all-you-need.pdf"
confidence: high
---

# Transformer Architecture

The Transformer is a neural network architecture that processes sequences entirely through **attention mechanisms**, without any recurrence (RNN) or convolution. Introduced in 2017, it became the foundation of all modern large language models.

## Why it matters

Before Transformers, sequence models (LSTMs, GRUs) processed tokens one-by-one — slow, and struggled to retain context across long distances. Transformers process the **entire sequence in parallel**, making them both faster to train and better at long-range dependencies.

## Core components

```
Input → Embedding + Positional Encoding
      → N × [Multi-Head Self-Attention → Add & Norm → FFN → Add & Norm]
      → Output Projection
```

- **Self-Attention**: each token computes how much it should "attend to" every other token
- **Multi-Head**: run attention H times in parallel with different learned projections → captures different relationship types simultaneously
- **Positional Encoding**: since there's no recurrence, position info is injected via sinusoidal signals added to embeddings
- **FFN (Feed-Forward Network)**: two linear layers with ReLU, applied per-token independently

## Attention formula

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

- Q (Query), K (Key), V (Value) — projections of the input
- Scaling by $\sqrt{d_k}$ prevents softmax saturation in high dimensions

## Key numbers (original paper)

| Config | d_model | Heads | Layers | FFN dim | Params |
|--------|---------|-------|--------|---------|--------|
| Base   | 512     | 8     | 6      | 2048    | 65M    |
| Large  | 1024    | 16    | 6      | 4096    | 213M   |

## Impact

Every major LLM (GPT, BERT, T5, Claude, Gemini) is a Transformer variant. The architecture proved general enough to extend beyond NLP → vision (ViT), audio, code, multimodal.

## See also

- [[concepts/attention-mechanism]] — the core operation in detail
- [[summaries/attention-is-all-you-need]] — source paper summary
- [[domains/ai]] — AI domain overview
