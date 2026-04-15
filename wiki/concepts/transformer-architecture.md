---
title: "Transformer Architecture"
domain: ai
tags: [transformer, attention, neural-network, deep-learning, nlp]
created: 2026-04-10
updated: 2026-04-10
source: "web search 2026-04-10"
confidence: medium
---

# Transformer Architecture

> Kiến trúc neural network dựa trên self-attention, cách mạng hóa NLP và trở thành nền tảng cho LLMs hiện đại.

## Định nghĩa

**Transformer** là kiến trúc neural network được giới thiệu trong paper *"Attention Is All You Need"* (Vaswani et al., 2017). Thay thế hoàn toàn recurrent/convolutional layers bằng **self-attention mechanism**, cho phép xử lý song song toàn bộ sequence.

Tại sao quan trọng: Transformer là nền tảng của GPT, BERT, và mọi LLM hiện đại. Nó giải quyết được bài toán long-range dependencies mà RNN/LSTM gặp khó khăn.

## Core Components

### 1. Self-Attention
Mỗi token tạo ra 3 vector: **Query** (tìm gì?), **Key** (chứa gì?), **Value** (cung cấp thông tin gì?).

```
Attention(Q, K, V) = softmax(QKᵀ / √dₖ) · V
```

- `√dₖ` scaling: prevent softmax gradient quá nhỏ khi dₖ lớn
- Mỗi token attend đến **tất cả** tokens khác → O(1) path length cho long-range dependencies

### 2. Multi-Head Attention
- Chạy nhiều attention heads song song, mỗi head học **loại quan hệ khác nhau**
- Output concatenate + linear projection
- Cho phép model jointly attend information từ nhiều representation subspaces

### 3. Encoder-Decoder Structure
- **Encoder**: Self-attention + Feed-Forward Network (FFN) + Residual + LayerNorm
- **Decoder**: Masked self-attention (không nhìn future tokens) + Cross-attention (nhìn encoder output) + FFN

### 4. Positional Encoding
- Transformer không có recurrence → cần encode position tường minh
- Sinusoidal functions hoặc learned embeddings

## 3 Variants chính

| Variant | Ví dụ | Phù hợp cho |
|---------|-------|-------------|
| **Encoder-only** | BERT | Understanding tasks (classification, NER) |
| **Decoder-only** | GPT | Generation tasks (text, code) |
| **Encoder-Decoder** | T5, BART | Seq2seq tasks (translation, summarization) |

## Ưu điểm so với RNN/LSTM

- **Parallelization**: tất cả positions tính song song → training nhanh hơn nhiều
- **Long-range dependencies**: O(1) path length thay vì O(n) như RNN
- **Scalability**: enable models từ hàng trăm triệu → hàng nghìn tỷ parameters

## Trade-offs

| Ưu điểm | Hạn chế |
|---------|---------|
| Song song hóa tốt | O(n²) attention → tốn memory cho long sequences |
| Scalable | Cần nhiều data và compute để train |
| Flexible architecture | Positional encoding không hoàn hảo |

## See also

- [[mlops-iqa-pipeline]] — Pipeline training có thể dùng Transformer backbone
- [[mlflow]] — Track Transformer model experiments
- [[pytorch]] — Framework phổ biến nhất để implement Transformer

---

*Imputed via web search — 2026-04-10*
