# RAG Retrieval Tuning Summary

## 背景

本次修改聚焦於港股輿情分析 RAG 模塊中的 retrieval 實驗。原始實驗存在 `accuracy` 和 `recall` 偏低的問題，並且測試查詢的構造方式容易把原文自己檢索回來，導致評估結果失真。

本輪調整的目標是：

- 修正檢索評估口徑，避免自匹配污染指標。
- 改善檢索文本與查詢文本的構造方式，提高同主題新聞的召回概率。
- 將 Hugging Face 的 Qwen embedding pooling 改為更合適的策略並重跑實驗。
- 支持中斷後續跑，避免索引重建浪費時間。

## 測試數據

- `C:\Users\Sirena.sr.Wang\Downloads\sentiment_input_batch.json`
- `C:\Users\Sirena.sr.Wang\Downloads\sentiment_input_with_prices.json`

這兩份文件都可用於測試，其中本次重跑實驗使用的是 `sentiment_input_batch.json`。此前已核對過，`sentiment_input_with_prices.json` 主要是在原有樣本上增加價格字段，對 retrieval 評估使用到的文本與標註字段沒有本質差異。

## 代碼修改

### 1. 評估邏輯修正

修改文件：

- `evaluation/retrieval_eval.py`

主要調整：

- 在計分前排除 `source_text_id` / `exclude_text_ids`，避免原文自身被算作命中。
- 對 `retrieved_ids` 和 `relevant_ids` 做標準化清洗，減少空值與格式差異導致的誤判。
- 移除對 `numpy` 的依賴，改為標準庫計算平均值與 `log2`。

這一部分解決了此前「看似命中、實際是把查詢來源文檔自己搜回來」的偏差問題。

### 2. 更合理的測試查詢與相關文檔標註

新增文件：

- `evaluation/retrieval_experiment_utils.py`

主要能力：

- `normalize_stock_code`：統一股票代碼為 `00000.HK` 格式。
- `build_searchable_text`：把標題、股票名稱、股票代碼、來源類型、正文拼成更利於檢索的文本。
- `generate_test_queries_from_documents`：從原始文檔生成更貼近真實查詢的測試集。
- `select_relevant_documents`：不再把同股票全部文檔都算相關，而是基於主題詞重合度與時間接近度挑選真正相似的文檔。

這讓評估集更貼近「同一支股票下的相近事件檢索」，而不是過於寬鬆的「同股票即相關」。

### 3. 向量庫與檢索策略調整

修改文件：

- `vector_storage.py`
- `run_rag_retrieval_experiment.py`

主要調整：

- 顯式支持 `EMBEDDING_BACKEND` 切換：`local / openai / dashscope / hf / auto`。
- 增加本地 deterministic hash embedding fallback，避免外部嵌入不可用時整個流程中斷。
- `add_text()` 改為對更完整的 `search_text` 做嵌入，而不是只嵌正文。
- 查詢階段增加股票代碼歸一化與查詢擴展。
- hybrid retrieval 改為以 RRF 為主的融合方式，較純分數歸一化更穩定。
- 新增 `reset_collection()` 和 `get_indexed_text_ids()`。
- 實驗腳本支持：
  - `--data-path`
  - `--keep-existing-index`

這一部分改善了文本可檢索性，也讓長時間實驗在中斷後可以續跑。

### 4. Hugging Face Qwen embedding pooling 調整

修改文件：

- `vector_storage.py`

本次最關鍵的調整是 Hugging Face Qwen embedding 的 pooling 方式。

之前常見做法是 mean pooling，但對 Qwen embedding 類模型來說，使用：

- `padding_side="left"`
- `last token pooling`
- 向量 `L2 normalize`
- 最終轉為 `float32`

會更符合模型設計與官方常見用法。

因此現在的邏輯是：

- 對 Qwen 類模型默認使用 `last token pooling`
- 對非 Qwen 類模型保留 mean pooling
- 也可通過 `HF_POOLING` 顯式覆蓋

## 實驗結果

### 基線結果

基線為本地 fallback embedding 路徑，指標如下：

| 指標 | 基線 |
| --- | ---: |
| Top-1 Accuracy | 0.5667 |
| Top-5 Recall | 0.5278 |
| MRR | 0.6650 |
| NDCG@5 | 0.5076 |
| Avg Retrieval Latency | 35.62 ms |

### 調整後結果

本次最終重跑配置：

- Embedding backend: `hf`
- Model: `Qwen/Qwen3-Embedding-0.6B`
- Data source: `C:\Users\Sirena.sr.Wang\Downloads\sentiment_input_batch.json`
- Hybrid retrieval: enabled
- Enhanced embedding: enabled

結果如下：

| 指標 | 調整後 |
| --- | ---: |
| Top-1 Accuracy | 0.8000 |
| Top-5 Recall | 0.4944 |
| MRR | 0.8114 |
| NDCG@5 | 0.5454 |
| Avg Retrieval Latency | 3304.22 ms |

### 提升情況

| 指標 | 基線 | 調整後 | 變化 |
| --- | ---: | ---: | ---: |
| Top-1 Accuracy | 0.5667 | 0.8000 | +0.2333 |
| Top-5 Recall | 0.5278 | 0.4944 | -0.0334 |
| MRR | 0.6650 | 0.8114 | +0.1464 |
| NDCG@5 | 0.5076 | 0.5454 | +0.0378 |
| Avg Retrieval Latency | 35.62 ms | 3304.22 ms | +3268.60 ms |

## 結論

本輪調整後，檢索排序質量有明顯提升：

- Top-1 Accuracy 大幅提升，說明第一條結果更常命中真正相關文檔。
- MRR 與 NDCG@5 也有明顯改善，說明前幾條結果的排序質量更好。
- Top-5 Recall 有小幅下降，代表當前策略更偏向提升排序精度，而不是擴大召回覆蓋。

代價也很明顯：

- 使用 `Qwen/Qwen3-Embedding-0.6B` 的 CPU 推理延遲顯著上升。

## 當前建議

如果下一步要繼續優化，優先建議：

1. 針對 recall 做 hybrid 參數調整，例如拉大 BM25 候選池或重新調整 dense / BM25 權重。
2. 對 HF embedding 增加批量化、cache 或 GPU 推理，降低查詢延遲。
3. 針對港股新聞的事件類型補充更細粒度的 query expansion 規則，提升同事件不同表述的召回。

## 驗證

已通過單元測試：

```bash
python -m unittest test_retrieval_eval.py test_retrieval_experiment_utils.py
```

最新實驗結果已寫入：

- `rag_experiment_results.json`
