---
title: "Attention Is All You Need"
domain: ai
tags: [transformer, attention, nlp, architecture]
created: 2017-06-12
updated: 2025-01-01
source: "raw/papers/attention-is-all-you-need.pdf"
confidence: high
---

# Attention Is All You Need

**Authors:** Vaswani et al. (Google Brain / Google Research), 2017  
**Venue:** NeurIPS 2017  
**arXiv:** 1706.03762

## Core Claim

Recurrence and convolution are unnecessary for sequence transduction. A model built **entirely on attention** achieves better translation quality, trains faster (parallelizable), and generalizes better.

## Problem

Dominant sequence models (LSTM, GRU) are sequential by nature — step N depends on step N-1. This creates two problems:
1. **Training bottleneck**: can't parallelize across time steps
2. **Long-range degradation**: information from early tokens gets diluted over many steps

## Architecture

The Transformer uses an **encoder-decoder** structure:
- **Encoder**: maps input sequence to continuous representations
- **Decoder**: generates output sequence one token at a time, attending to both its own previous outputs and the encoder output

Each block (×6 in the base model) consists of:
1. Multi-Head Self-Attention
2. Position-wise Feed-Forward Network
3. Residual connections + Layer Norm around each sub-layer

## Key Innovations

**Multi-Head Attention** — run attention h=8 times in parallel with different learned subspaces. Each head can specialize in a different relationship type (syntax, coreference, semantics). Outputs are concatenated and projected.

**Scaled Dot-Product Attention** — $\text{softmax}(QK^T / \sqrt{d_k})V$. The $\sqrt{d_k}$ scaling matters: without it, dot products grow large in high dimensions, pushing softmax into near-zero gradient regions.

**Positional Encoding** — sinusoidal functions of different frequencies. Allows the model to learn relative positions; also generalizes to sequence lengths longer than those seen in training.

**No recurrence** → full parallelism during training. On WMT 2014 EN→DE, the large Transformer trained in 3.5 days on 8 P100 GPUs vs. weeks for prior models.

## Results

| Task | BLEU | Notes |
|------|------|-------|
| EN→DE translation | 28.4 | +2.0 over prior SOTA |
| EN→FR translation | 41.0 | New SOTA at fraction of training cost |
| English constituency parsing | 91.3 F1 | With minimal tuning |

## Why It Matters

This paper didn't just improve translation — it eliminated an entire class of assumptions about sequence modeling. The architecture generalized immediately: BERT (2018), GPT (2018), T5, and every LLM since are Transformer variants. The "attention is all you need" thesis turned out to apply far beyond NLP.

## Limitations

- Quadratic complexity in sequence length: $O(n^2 \cdot d)$ — becomes expensive for very long contexts
- No built-in notion of position (requires positional encoding as a workaround)
- Large memory footprint during training

## Key Concepts

- [[concepts/transformer-architecture]] — full architecture breakdown
- [[concepts/attention-mechanism]] — the core operation

## Relations

- Led to: BERT, GPT series, T5, ViT (vision), Whisper (audio)
- Domain MOC: [[domains/ai]]
