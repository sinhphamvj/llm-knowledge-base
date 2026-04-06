---
title: "Attention Is All You Need"
domain: ai
tags: [transformer, attention, nlp, architecture]
created: 2017-06-12
updated: 2026-04-06
source: "raw/papers/attention-is-all-you-need.pdf"
confidence: high
---

# Attention Is All You Need

**Tác giả:** Vaswani et al. (Google Brain / Google Research), 2017  
**Hội nghị:** NeurIPS 2017  
**arXiv:** 1706.03762

## Luận điểm chính

Recurrence (hồi quy) và convolution (tích chập) là không cần thiết cho bài toán sequence transduction. Một mô hình xây dựng **hoàn toàn trên attention** đạt chất lượng dịch tốt hơn, huấn luyện nhanh hơn (có thể song song hóa), và tổng quát hóa tốt hơn.

## Vấn đề

Các mô hình sequence thống trị trước đó (LSTM, GRU) có bản chất tuần tự — bước N phụ thuộc bước N-1. Điều này gây ra hai vấn đề:
1. **Nghẽn cổ chai khi huấn luyện**: không thể song song hóa qua các bước thời gian
2. **Suy giảm thông tin tầm xa**: thông tin từ các token đầu bị pha loãng qua nhiều bước

## Kiến trúc

Transformer dùng cấu trúc **encoder-decoder**:
- **Encoder**: ánh xạ chuỗi đầu vào thành các biểu diễn liên tục
- **Decoder**: sinh chuỗi đầu ra từng token một, chú ý đến cả output trước đó và output của encoder

Mỗi block (×6 trong mô hình base) gồm:
1. Multi-Head Self-Attention
2. Position-wise Feed-Forward Network
3. Residual connections + Layer Norm quanh mỗi sub-layer

## Các đổi mới chính

**Multi-Head Attention** — chạy attention h=8 lần song song với các không gian con học được khác nhau. Mỗi head có thể chuyên biệt cho một loại mối quan hệ khác nhau (cú pháp, coreference, ngữ nghĩa). Output được ghép nối và chiếu lại.

**Scaled Dot-Product Attention** — $\text{softmax}(QK^T / \sqrt{d_k})V$. Việc chia cho $\sqrt{d_k}$ rất quan trọng: nếu không, tích vô hướng phát triển lớn trong không gian chiều cao, đẩy softmax vào vùng gradient gần bằng 0.

**Positional Encoding** — các hàm sinusoidal với tần số khác nhau. Cho phép mô hình học vị trí tương đối; cũng tổng quát hóa được cho độ dài chuỗi dài hơn so với lúc huấn luyện.

**Không có recurrence** → song song hóa hoàn toàn khi huấn luyện. Trên WMT 2014 EN→DE, Transformer lớn huấn luyện trong 3.5 ngày trên 8 GPU P100, so với nhiều tuần với các mô hình trước.

## Kết quả

| Tác vụ | BLEU | Ghi chú |
|--------|------|---------|
| Dịch EN→DE | 28.4 | +2.0 so với SOTA trước |
| Dịch EN→FR | 41.0 | SOTA mới với chi phí huấn luyện thấp hơn |
| Phân tích cú pháp tiếng Anh | 91.3 F1 | Với điều chỉnh tối thiểu |

## Tại sao quan trọng

Bài báo này không chỉ cải thiện dịch thuật — nó loại bỏ hoàn toàn một lớp giả định về sequence modeling. Kiến trúc tổng quát hóa ngay lập tức: BERT (2018), GPT (2018), T5, và mọi LLM kể từ đó đều là biến thể của Transformer. Luận điểm "attention is all you need" hóa ra áp dụng được jauh hơn NLP rất nhiều.

## Hạn chế

- Độ phức tạp bậc hai theo độ dài chuỗi: $O(n^2 \cdot d)$ — trở nên đắt với ngữ cảnh rất dài
- Không có khái niệm vị trí tích hợp sẵn (cần positional encoding như một giải pháp tạm)
- Bộ nhớ lớn trong quá trình huấn luyện

## Các khái niệm chính

- [[concepts/transformer-architecture]] — phân tích kiến trúc đầy đủ
- [[concepts/attention-mechanism]] — phép toán cốt lõi

## Liên kết

- Dẫn đến: BERT, GPT series, T5, ViT (vision), Whisper (audio)
- Domain MOC: [[domains/ai]]
