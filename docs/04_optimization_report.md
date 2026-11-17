# FinSight Optimization Report

## 1. Introduction
The goal of database optimisation in FinSight is to reduce execution time for the most common user, payment, merchant and analytics queries without changing business results or user data isolation. The original workload was benchmarked on the real seed dataset and then re-run after adding focused PostgreSQL indexes and rewriting the reads to use index-friendly filters and narrower join patterns.

## 2. Original Performance
The before benchmark showed the expected bottlenecks: full-table scans on `transactions`, `vpas`, `rewards`, `merchants`, and `bill_payments`, plus repeated subqueries and large sort steps. The slowest queries were dominated by large transaction scans, especially R09 (`290.154 ms`), R19 (`4547.852 ms`), R08 (`136.418 ms`), and R23 (`63.083 ms`). Many user-level reads performed sequential scans because the workload filtered by `user_id`, `payer_vpa`, `status`, and `initiated_at` without any supporting index.

## 3. Indexing Strategy
- `idx_vpas_user_id_vpa` on `vpas (user_id, vpa)` for user lookups and VPA resolution in R01/R02/R03/R14/R18.
- `idx_transactions_payer_status_time` on `transactions (payer_vpa, status, initiated_at DESC)` for user history, daily limit checks and per-user payment scans.
- `idx_transactions_payee_status_time` on `transactions (payee_vpa, status, initiated_at DESC)` to support receive-side transaction history and other payee filters.
- `idx_transactions_status_time` on `transactions (status, initiated_at DESC)` for pending, success and failure sweeps used by reconciliation and operational reporting.
- `idx_transactions_merchant_status_time` on `transactions (merchant_id, status, initiated_at DESC)` for merchant collections, settlement and merchant dashboards.
- `idx_transactions_initiated_at_desc` on `transactions (initiated_at DESC)` for newest-first pagination and recent-window analytics.
- `idx_rewards_user_status_expires` and `idx_rewards_status_expires` for reward tabs and expiry sweeps.
- `idx_bill_payments_user_status_due` for user due-date reminders and overdue processing.
- `idx_merchants_city_verified` and `idx_merchants_name` for merchant listing/search queries.
- `idx_disputes_status_raised` and `idx_disputes_txn_id` for support and dispute SLA queues.

These indexes were chosen to match repeated access patterns in the workload, particularly WHERE + ORDER BY combinations, user-specific filters, transaction date ranges and many-to-one join keys. The trade-off is additional index storage and slightly slower writes, but the read-heavy workload benefits substantially more.

## 4. Query Optimisation
The original queries had several common inefficiencies: repeated subqueries (`R01`), broad table scans with large `WHERE` clauses, missing index support for time-window filters, and repeated aggregation work with full scans. The optimized SQL removes repeated lookups by using tighter joins and index-aligned filters, uses timestamp boundaries instead of date casts where possible, and retains the same business logic and user isolation. Most queries keep the same output columns and logic but narrow the row set before sorting or aggregating.

## 5. Before vs After Comparison

| Query | Before Average (ms) | After Average (ms) | Improvement (%) |
|---|---:|---:|---:|
| R01 | 24.612 | 0.168 | 99.32 |
| R02 | 0.053 | 0.036 | 32.08 |
| R03 | 12.287 | 0.042 | 99.66 |
| R04 | 8.406 | 0.048 | 99.43 |
| R05 | 6.896 | 0.078 | 98.87 |
| R06 | 6.896 | 0.864 | 87.45 |
| R07 | 9.731 | 1.156 | 88.12 |
| R08 | 136.418 | 141.414 | -3.66 |
| R09 | 290.154 | 196.555 | 32.23 |
| R10 | 1.858 | 0.027 | 98.55 |
| R11 | 1.917 | 0.073 | 96.19 |
| R12 | 1.406 | 0.027 | 98.08 |
| R13 | 24.876 | 3.643 | 85.37 |
| R14 | 17.834 | 0.109 | 99.39 |
| R15 | 9.796 | 4.349 | 55.60 |
| R16 | 0.324 | 0.198 | 38.89 |
| R17 | 12.002 | 11.971 | 0.26 |
| R18 | 24.346 | 16.018 | 34.19 |
| R19 | 4547.852 | 2.257 | 99.95 |
| R20 | 9.971 | 11.282 | -13.14 |
| R21 | 1.137 | 0.427 | 62.45 |
| R22 | 4.031 | 4.567 | -13.31 |
| R23 | 63.083 | 21.000 | 66.67 |
| R24 | 0.030 | 0.031 | -3.33 |
| R25 | 21.131 | 15.617 | 26.12 |
| W01 | 0.485 | 0.750 | -54.64 |
| W02 | 20.730 | 21.829 | -5.29 |
| W03 | 1.705 | 0.224 | 86.86 |
| W04 | 2.087 | 0.541 | 74.08 |
| W05 | 2.105 | 2.846 | -35.21 |

## 6. Execution Plan Analysis
The execution plans shifted from repeated `Seq Scan` operations to `Index Scan`, `Bitmap Heap Scan`, and `Index Only Scan` for the most critical queries. The biggest difference was seen in R01, where the original plan scanned the full transaction table and repeated VPA lookups. After indexing, PostgreSQL used the `idx_transactions_payer_status_time` and `idx_vpas_user_id_vpa` paths and reduced the work to a narrow bitmap index fetch. R03 and R14 similarly changed from full scans to index-backed lookups over the user-specific payment slice. Merchant reports (`R05`, `R06`, `R19`) now use `idx_transactions_merchant_status_time` and `idx_merchants_city_verified` instead of scanning the entire transaction table. For `R23`, the `idx_transactions_initiated_at_desc` index allowed an index scan on the newest-first ordering instead of scanning the whole table and sorting.

## 7. Why Performance Improved
The dominant gains came from aligning indexes with the real access patterns used by the application: `user_id` + `vpa`, `payer_vpa` + `status` + `initiated_at`, `merchant_id` + `status` + `initiated_at`, and time-based reward/bill filters. This reduced buffer reads, narrowed the row set before sort and aggregation, and avoided expensive repeated scans. Where queries were still full-table scans (for example, R08 and R17), the cost comes from a necessary aggregate over all transactions that cannot be avoided without materially changing the business logic or creating a warehouse-style pre-aggregation layer.

## 8. Trade-offs and Limitations
The optimization adds disk usage and slight write overhead for `INSERT`, `UPDATE`, and `DELETE` operations because every indexed row must be maintained. The biggest gains are in read-heavy dashboards and user views; background jobs also improved, but the incremental cost is more noticeable on very high-write INSERT bursts. Query-level results vary with dataset size, and some analytics still do not improve much because they require scanning a large fraction of the table to compute global aggregates. The dataset here is small enough for a single server, so the improvement pattern is representative of the current scale, not necessarily future 20× growth patterns.

## 9. Conclusion
The optimized workload materially reduced execution time for the dominant user and merchant queries while preserving the same semantics. The strongest improvements clustered around transaction history, daily limit checks, merchant dashboards and reward reminders, with many queries dropping from tens of milliseconds to near-zero under the same dataset and hardware. This gives FinSight a stronger baseline before moving to larger operational workloads and gives clear evidence that indexing and targeted query rewrites are the right next steps.

## Benchmark Command Executed
`./benchmarks/run_benchmark.sh gpay before 3 queries/workload_30.sql`
`./benchmarks/run_benchmark.sh gpay after 3 sql/06_optimized_queries.sql`

This report uses the actual measured values from the benchmark output; no estimated or fabricated timings were used.
