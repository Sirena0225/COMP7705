# Latest Data Experiment Report

## 1. Run Summary

- Run date: 2026-07-15
- Retrieval dataset: `data/sentiment_input_latest.json`
- Price-augmented dataset: `data/sentiment_input_with_prices_latest.json`
- Daily update summary: `data/daily_update_summary_10stocks_7days.json`
- Retrieval config:
  - embedding backend: `hf`
  - embedding model: `Qwen/Qwen3-Embedding-0.6B`
  - retrieval mode: hybrid retrieval
  - enhanced embedding: enabled
  - offline model loading: enabled via local Hugging Face cache

## 2. New Data Overview

### 2.1 File status

| File | Size | Last Updated |
| --- | ---: | --- |
| `data/daily_update_summary_10stocks_7days.json` | 2,961 bytes | 2026-07-15 00:49 |
| `data/sentiment_input_latest.json` | 95,791 bytes | 2026-07-15 00:49 |
| `data/sentiment_input_with_prices_latest.json` | 162,761 bytes | 2026-07-15 00:49 |

### 2.2 Daily update export summary

Based on `data/daily_update_summary_10stocks_7days.json`:

- target stocks: 10
- time window: 7 days
- fetched documents: 233
- inserted documents: 80
- fetched prices: 120
- inserted prices: 80
- daily feature rows: 721
- exported sentiment records: 137

### 2.3 Retrieval input statistics

Based on the latest retrieval run:

- document samples: 137
- source types:
  - `news`: 128
  - `announcement`: 9
- language distribution:
  - `en`: 137
- generated test queries: 27
- covered stock codes: 10

### 2.4 Note on the price-enhanced file

`data/sentiment_input_with_prices_latest.json` contains the same article-level records as `data/sentiment_input_latest.json`, but adds:

- `price_on_publish_date`
- `previous_trading_day_price`

These fields are useful for downstream sentiment-price linkage analysis, but they do not change the retrieval text fields. Therefore, the retrieval experiment in this run was executed on `data/sentiment_input_latest.json`.

## 3. Retrieval Experiment Results

### 3.1 Runtime

| Item | Value |
| --- | ---: |
| Vector store build time | 1013.61 s |
| Retrieval evaluation time | 104.98 s |
| Successfully indexed samples | 137 |
| Skipped existing samples | 0 |
| Average retrieval latency | 3888.12 ms |

### 3.2 Retrieval quality metrics

| Metric | Value |
| --- | ---: |
| Top-1 Accuracy | 0.5926 |
| Top-5 Recall | 0.7963 |
| MRR | 0.7257 |
| NDCG@5 | 0.6769 |
| Overall blended score | 0.6979 |

### 3.3 Interpretation

- The new dataset shows strong recall coverage: `Top-5 Recall = 0.7963`.
- Ranking quality within the top 5 results is also solid: `NDCG@5 = 0.6769`.
- However, the first-hit precision is weaker than the previous run: `Top-1 Accuracy = 0.5926`.
- CPU inference cost remains high for Qwen embedding, and latency increased further to about `3.89s` per retrieval query.

## 4. Comparison with the Previous Retrieval Run

### 4.1 Previous baseline used for comparison

The previous saved run in `rag_experiment_results.json` before this refresh used:

- data source: `C:\Users\Sirena.sr.Wang\Downloads\sentiment_input_batch.json`
- samples: 441
- test queries: 30
- embedding backend: `hf`
- model: `Qwen/Qwen3-Embedding-0.6B`

### 4.2 Metric comparison

Important note:

- the comparison below is useful for trend observation only
- it is not a strict apples-to-apples benchmark
- because the dataset changed from `441` samples / `30` queries to `137` samples / `27` queries

| Metric | Previous Run | New Run | Change |
| --- | ---: | ---: | ---: |
| Top-1 Accuracy | 0.8000 | 0.5926 | -0.2074 |
| Top-5 Recall | 0.4944 | 0.7963 | +0.3019 |
| MRR | 0.8114 | 0.7257 | -0.0857 |
| NDCG@5 | 0.5454 | 0.6769 | +0.1315 |
| Avg. Retrieval Latency (ms) | 3304.22 | 3888.12 | +583.90 |

### 4.3 Did the result improve?

The answer is mixed:

- If the goal is broader candidate coverage, the result improved.
  - `Top-5 Recall` increased significantly.
  - `NDCG@5` also improved.
- If the goal is getting the correct document at rank 1, the result did not improve.
  - `Top-1 Accuracy` dropped.
  - `MRR` also dropped.
- Efficiency did not improve.
  - retrieval latency increased by about `584 ms`.

### 4.4 Practical conclusion

For the new 10-stock, 7-day dataset:

- the current retrieval stack is better at finding relevant documents within the top 5
- but less reliable at placing the best relevant document in the first position

This suggests that the current search text construction and hybrid retrieval setup are helping recall, but the ranking calibration for the very top result may still need tuning.

## 5. Sentiment Analysis Summary

### 5.1 Analysis method

To ensure the run could complete locally without external API dependency, the sentiment summary below was generated with:

- analyzer: `MockLLMAnalyzer`
- mode: offline heuristic scoring
- input file: `data/sentiment_input_latest.json`

This section should be interpreted as a lightweight operational summary rather than a production-grade LLM inference benchmark.

### 5.2 Aggregate sentiment distribution

| Sentiment | Count |
| --- | ---: |
| Positive | 11 |
| Neutral | 122 |
| Negative | 4 |

- analyzed records: 137
- average sentiment score: `0.0095`

Overall, the latest dataset is close to neutral, with a slight positive tilt.

### 5.3 Average sentiment score by stock

| Stock Code | Avg. Sentiment Score |
| --- | ---: |
| `02318.HK` | 0.4000 |
| `03690.HK` | 0.0286 |
| `09988.HK` | 0.0208 |
| `01211.HK` | 0.0167 |
| `00700.HK` | 0.0148 |
| `09999.HK` | 0.0000 |
| `09888.HK` | -0.0071 |
| `09618.HK` | -0.0111 |
| `01810.HK` | -0.0125 |
| `00005.HK` | -0.0179 |

### 5.4 Top positive samples

| Stock | Score | Title |
| --- | ---: | --- |
| `02318.HK` | 0.4000 | `JPM: Positive Profit Alerts Boost Earnings Expectations for CN Insurers but Dividends Are Key; PING AN Preferred` |
| `09988.HK` | 0.2000 | `Nomura Projects Meager China E-commerce CMR for BABA-W in 1FQ, Cloud Revenue Growth to Accelerate` |
| `09988.HK` | 0.2000 | `JPM Forecasts BABA-W 1QFY27 Results to Beat, Raises Annual Adj. EPS Forecast by 2%` |
| `09988.HK` | 0.2000 | `BofAS Expects BABA-W Cloud to Deliver Strong Growth in 1FQ, Reiterates Buy Rating` |
| `00700.HK` | 0.2000 | `UBS Expects TENCENT 2Q Revenue to Climb 9% YoY, Adj. Net Profit to Lift 4%` |

### 5.5 Top negative samples

| Stock | Score | Title |
| --- | ---: | --- |
| `09618.HK` | -0.2500 | `Nomura Forecasts JD 2Q Adj. Profit to Rise 14% YoY, Maintains Buy Rating` |
| `01810.HK` | -0.2500 | `IDC: Global Smartphone Shipments Fall 6.7% YoY in 2Q as Memory Crisis Continues to Impact Market` |
| `09888.HK` | -0.2500 | `M Stanley Cuts Baidu TP to USD130, Expects AI Investment to Weigh on 2Q Core OP` |
| `00005.HK` | -0.2500 | `HSBC HOLDINGS Reportedly Seeks to Market Hang Seng's Risky Loans` |
| `09618.HK` | -0.0500 | `UBS Expects JD.com, Inc. 2Q26 Adj. Profit to Rise 14% YoY; Maintains Buy Rating` |

## 6. Final Assessment

### 6.1 Retrieval

The refreshed dataset did not produce a uniform improvement.

- Improved:
  - recall coverage
  - top-5 ranking quality
- Weakened:
  - top-1 hit rate
  - first relevant rank position
  - latency

### 6.2 Sentiment

The latest 7-day, 10-stock dataset is predominantly neutral in tone, with a small number of strongly positive and negative items. The strongest positive skew in this offline summary appears in `02318.HK`, while the weakest average sentiment appears in `00005.HK`, `01810.HK`, and `09618.HK`.

### 6.3 Recommended next steps

1. Tune the hybrid fusion weights or candidate pool size to recover top-1 precision without losing recall.
2. Add a reranker layer for the final top 5 candidates.
3. Batch query embeddings or move Qwen embedding inference to GPU to reduce latency.
4. If the report requires production-grade sentiment results, rerun the same dataset with the real multilingual analyzer instead of the offline mock analyzer.
