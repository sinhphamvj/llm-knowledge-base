---
title: "Transformer Architecture"
domain: ai
tags: [architecture, attention, deep-learning, nlp]
created: 2017-06-12
updated: 2026-04-06
source: "raw/papers/attention-is-all-you-need.pdf"
confidence: high
---

# Transformer Architecture

Transformer là kiến trúc mạng nơ-ron xử lý chuỗi hoàn toàn thông qua **cơ chế attention**, không dùng recurrence (RNN) hay convolution. Ra đời năm 2017, nó trở thành nền tảng của mọi mô hình ngôn ngữ lớn hiện đại.

## Tại sao quan trọng

Trước Transformer, các mô hình chuỗi (LSTM, GRU) xử lý token từng cái một — chậm và khó giữ ngữ cảnh tầm xa. Transformer xử lý **toàn bộ chuỗi song song**, vừa huấn luyện nhanh hơn vừa nắm bắt tốt hơn các phụ thuộc tầm xa.

## Các thành phần cốt lõi

```
Input → Embedding + Positional Encoding
      → N × [Multi-Head Self-Attention → Add & Norm → FFN → Add & Norm]
      → Output Projection
```

- **Self-Attention**: mỗi token tính toán mức độ nên "chú ý" đến mọi token khác
- **Multi-Head**: chạy attention H lần song song với các phép chiếu học được khác nhau → nắm bắt nhiều loại mối quan hệ cùng lúc
- **Positional Encoding**: vì không có recurrence, thông tin vị trí được bổ sung qua tín hiệu sinusoidal cộng vào embedding
- **FFN (Feed-Forward Network)**: hai lớp tuyến tính với ReLU, áp dụng độc lập cho từng token

## Công thức Attention

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

- Q (Query), K (Key), V (Value) — các phép chiếu của đầu vào
- Chia cho $\sqrt{d_k}$ để tránh softmax bão hòa ở chiều cao

## Thông số chính (bài báo gốc)

| Cấu hình | d_model | Heads | Layers | FFN dim | Params |
|----------|---------|-------|--------|---------|--------|
| Base     | 512     | 8     | 6      | 2048    | 65M    |
| Large    | 1024    | 16    | 6      | 4096    | 213M   |

## Tầm ảnh hưởng

Mọi LLM lớn (GPT, BERT, T5, Claude, Gemini) đều là biến thể của Transformer. Kiến trúc đủ tổng quát để mở rộng ra ngoài NLP → thị giác (ViT), âm thanh, code, đa phương thức.

## Xem thêm

- [[concepts/attention-mechanism]] — phép toán cốt lõi chi tiết
- [[summaries/attention-is-all-you-need]] — tóm tắt bài báo nguồn
- [[domains/ai]] — tổng quan domain AI
