# Baseline Query Execution Timings

### 1. Objective

The objective of this report is to establish the unoptimized baseline PostgreSQL execution timings for the 30-query Google Pay (UPI) workload (`queries/workload_30.sql`), consisting of 25 read queries (`R01`–`R25`) and 5 write queries (`W01`–`W05`). Each query was executed exactly 3 times against the baseline schema (`sql/01_schema.sql`) and seed dataset (`seed_data.zip`) using the repository's official benchmark script (`benchmarks/run_benchmark.sh`), yielding 90 measured query executions.

---

### 2. Benchmark Environment

- **Database:** PostgreSQL (`gpay` database, `gpay` schema)
- **PostgreSQL version:** PostgreSQL 18.6 (Postgres.app)
- **Operating system:** macOS 27.2 (Build 26B123, `arm64`)
- **Machine / environment details:** Apple M4, 16 GB RAM (17,179,869,184 bytes)
- **Dataset used:** `seed_data.zip` loaded via `sql/02_load_data.sql` followed by `ANALYZE`:
  - `cities`: 10 rows
  - `users`: 40,000 rows
  - `bank_accounts`: 53,333 rows
  - `vpas`: 53,333 rows
  - `merchants`: 3,000 rows
  - `transactions`: 250,468 rows
  - `bill_payments`: 30,000 rows
  - `rewards`: 39,799 rows
  - `disputes`: 3,569 rows
- **Baseline indexes present (automatic PK/UNIQUE constraints only):**
  - `cities_pkey` (`cities.city_id`)
  - `users_pkey` (`users.user_id`)
  - `bank_accounts_pkey` (`bank_accounts.account_id`)
  - `vpas_pkey` (`vpas.vpa`)
  - `merchants_pkey` (`merchants.merchant_id`)
  - `transactions_pkey` (`transactions.txn_id`)
  - `transactions_upi_ref_key` (`transactions.upi_ref`)
  - `bill_payments_pkey` (`bill_payments.bill_id`)
  - `rewards_pkey` (`rewards.reward_id`)
  - `disputes_pkey` (`disputes.dispute_id`)
- **Workload file:** `queries/workload_30.sql`
- **Benchmark script:** `benchmarks/run_benchmark.sh`
- **Number of workload queries:** 30 (`R01`–`R25`, `W01`–`W05`)
- **Number of measured runs per query:** 3 (90 total measured executions)

---

### 3. Benchmark Methodology

1. **Execution Mechanism:** The benchmark was executed using the official script `./benchmarks/run_benchmark.sh gpay baseline`, which splits `queries/workload_30.sql` on `-- @R01` … `-- @W05` markers into individual SQL statements and runs each query `RUNS=3` times in sequence using `psql -d gpay -X -q -A -t -v ON_ERROR_STOP=1`.
2. **Timing Measurement:** Each query execution runs with `SET search_path TO gpay; EXPLAIN (ANALYZE, BUFFERS) <query>`. The script extracts the `Execution Time` reported by PostgreSQL (in milliseconds) from each of the 3 runs and saves the full query plans for all 3 runs in `benchmarks/results/baseline/<query_id>.txt`.
3. **Warm-up Runs:** `benchmarks/run_benchmark.sh` does not perform separate unrecorded warm-up runs; all 3 executions per query (`run 1`, `run 2`, `run 3`) are directly recorded and included in the calculation.
4. **Dataset Consistency Across Runs:** The exact same database and seed dataset were used across all 3 runs of all 30 queries. For write queries (`W01`–`W05`), `benchmarks/run_benchmark.sh` wraps every single execution inside a transaction block that rolls back immediately after measuring:
   ```sql
   SET search_path TO gpay; BEGIN; EXPLAIN (ANALYZE, BUFFERS) <query> ROLLBACK;
   ```
   This guarantees that `INSERT` and `UPDATE` statements do not modify the underlying dataset between runs.
5. **Average Calculation:** For each query, the average execution time (in milliseconds, rounded to 3 decimal places) is calculated as:
   $$\text{Average} = \frac{\text{Run 1} + \text{Run 2} + \text{Run 3}}{3}$$

---

### 4. Detailed Query Timings

All execution times below are in **milliseconds (ms)** and match the raw `EXPLAIN (ANALYZE, BUFFERS)` plan files (`benchmarks/results/baseline/*.txt`) and `benchmarks/results/baseline/summary.csv`.

| Query ID | Query Description | Run 1 | Run 2 | Run 3 | Average |
|----------|-------------------|-------|-------|-------|---------|
| R01 | Transaction history: everything user 15177 sent or received, newest first | 31.386 ms | 27.206 ms | 27.877 ms | 28.823 ms |
| R02 | "Pay to UPI ID": check that the entered VPA exists and is active | 0.074 ms | 0.064 ms | 0.065 ms | 0.068 ms |
| R03 | UPI limit check: total successfully sent by user 15177 on 30 June 2026 (limit ₹1,00,000/day) | 22.419 ms | 22.444 ms | 22.448 ms | 22.437 ms |
| R04 | Reconciliation: payments still PENDING more than 15 minutes after 23:59 on 30 Jun 2026 | 14.378 ms | 13.842 ms | 14.333 ms | 14.184 ms |
| R05 | Google Pay for Business: hourly collections of merchant 2 on 29 June 2026 | 12.639 ms | 12.429 ms | 12.464 ms | 12.511 ms |
| R06 | Settlement: amount to settle to every merchant for 29 June 2026 | 12.741 ms | 12.662 ms | 12.783 ms | 12.729 ms |
| R07 | Bank health: failure codes per payer bank in the last 7 days | 13.654 ms | 13.250 ms | 13.524 ms | 13.476 ms |
| R08 | Fraud: VPAs that received P2P money from 5+ different people on the same day | 253.714 ms | 250.373 ms | 251.132 ms | 251.740 ms |
| R09 | Fraud: repeated payments—same payer to the same payee within 10 minutes of the previous one | 567.013 ms | 545.720 ms | 549.375 ms | 554.036 ms |
| R10 | Rewards tab: user 15177's unscratched cards that have not expired | 2.893 ms | 3.069 ms | 2.855 ms | 2.939 ms |
| R11 | Notification job: unscratched rewards that expire in the first 3 days of July | 3.230 ms | 3.378 ms | 3.250 ms | 3.286 ms |
| R12 | Bill reminders: user 1072's unpaid bills due in the next 7 days | 2.331 ms | 2.308 ms | 2.306 ms | 2.315 ms |
| R13 | Merchant success team: merchants who have never received a payment (to call and help them) | 45.253 ms | 46.990 ms | 46.750 ms | 46.331 ms |
| R14 | Spend analysis: user 15177's 2026 spending per merchant category code (MCC) | 33.028 ms | 32.978 ms | 32.163 ms | 32.723 ms |
| R15 | Business insights: top 10 merchants by June 2026 GMV in each city | 17.595 ms | 18.080 ms | 17.895 ms | 17.857 ms |
| R16 | Disputes desk: disputes open for more than 7 days (SLA breached) | 0.571 ms | 0.590 ms | 0.577 ms | 0.579 ms |
| R17 | Merchant risk: refund rate per merchant (at least 30 payments) | 22.161 ms | 21.994 ms | 22.001 ms | 22.052 ms |
| R18 | Compliance: users without verified KYC who have successfully sent ₹10,000+ in total | 43.685 ms | 44.160 ms | 43.000 ms | 43.615 ms |
| R19 | Merchant report: last payment time and successful payment count of every verified Bengaluru merchant | 8290.232 ms | 8342.709 ms | 8270.024 ms | 8300.988 ms |
| R20 | Platform health: daily success rate in June 2026 | 20.132 ms | 19.905 ms | 20.318 ms | 20.118 ms |
| R21 | "Search businesses": merchants with "chai" in their name | 2.180 ms | 2.359 ms | 2.189 ms | 2.243 ms |
| R22 | Payment screen: user 15177's primary bank account and all their UPI IDs | 7.885 ms | 8.033 ms | 8.056 ms | 7.991 ms |
| R23 | Operations console: all transactions, newest first, page 8,001 (25 per page) | 122.398 ms | 127.380 ms | 124.157 ms | 124.645 ms |
| R24 | Customer support: find a payment by its UPI reference number | 0.057 ms | 0.069 ms | 0.056 ms | 0.061 ms |
| R25 | Bank health: average seconds from initiation to completion per payer bank (June 2026) | 39.423 ms | 39.675 ms | 39.119 ms | 39.406 ms |
| W01 | Pay: user 15177 starts a ₹250 payment to merchant 2 (PENDING until the bank confirms) | 1.013 ms | 0.944 ms | 0.883 ms | 0.947 ms |
| W02 | Bank callback: mark the oldest PENDING payment as successful | 39.584 ms | 40.819 ms | 39.905 ms | 40.103 ms |
| W03 | Scratch card: user 15177 scratches their oldest unscratched card | 3.005 ms | 2.940 ms | 2.998 ms | 2.981 ms |
| W04 | Nightly job (run at 00:00 on 4 Jul 2026): expire every reward whose time is up | 3.793 ms | 3.734 ms | 3.549 ms | 3.692 ms |
| W05 | Nightly job: bills past their due date and still unpaid become OVERDUE | 3.962 ms | 3.916 ms | 3.869 ms | 3.916 ms |
| **Total (sum of all 30)** | **All 30 workload queries (25 READ, 5 WRITE)** | **9632.429 ms** | **9664.020 ms** | **9589.921 ms** | **9628.792 ms** |

#### Phase 3 Reference Table (with Query Type)

| SQL Query | Type | Run 1 (ms) | Run 2 (ms) | Run 3 (ms) | Average (ms) |
|---|---|---:|---:|---:|---:|
| R01: Transaction history: everything user 15177 sent or received, newest first | READ | 31.386 | 27.206 | 27.877 | 28.823 |
| R02: "Pay to UPI ID": check that the entered VPA exists and is active | READ | 0.074 | 0.064 | 0.065 | 0.068 |
| R03: UPI limit check: total successfully sent by user 15177 on 30 June 2026 (limit ₹1,00,000/day) | READ | 22.419 | 22.444 | 22.448 | 22.437 |
| R04: Reconciliation: payments still PENDING more than 15 minutes after 23:59 on 30 Jun 2026 | READ | 14.378 | 13.842 | 14.333 | 14.184 |
| R05: Google Pay for Business: hourly collections of merchant 2 on 29 June 2026 | READ | 12.639 | 12.429 | 12.464 | 12.511 |
| R06: Settlement: amount to settle to every merchant for 29 June 2026 | READ | 12.741 | 12.662 | 12.783 | 12.729 |
| R07: Bank health: failure codes per payer bank in the last 7 days | READ | 13.654 | 13.250 | 13.524 | 13.476 |
| R08: Fraud: VPAs that received P2P money from 5+ different people on the same day | READ | 253.714 | 250.373 | 251.132 | 251.740 |
| R09: Fraud: repeated payments—same payer to the same payee within 10 minutes of the previous one | READ | 567.013 | 545.720 | 549.375 | 554.036 |
| R10: Rewards tab: user 15177's unscratched cards that have not expired | READ | 2.893 | 3.069 | 2.855 | 2.939 |
| R11: Notification job: unscratched rewards that expire in the first 3 days of July | READ | 3.230 | 3.378 | 3.250 | 3.286 |
| R12: Bill reminders: user 1072's unpaid bills due in the next 7 days | READ | 2.331 | 2.308 | 2.306 | 2.315 |
| R13: Merchant success team: merchants who have never received a payment (to call and help them) | READ | 45.253 | 46.990 | 46.750 | 46.331 |
| R14: Spend analysis: user 15177's 2026 spending per merchant category code (MCC) | READ | 33.028 | 32.978 | 32.163 | 32.723 |
| R15: Business insights: top 10 merchants by June 2026 GMV in each city | READ | 17.595 | 18.080 | 17.895 | 17.857 |
| R16: Disputes desk: disputes open for more than 7 days (SLA breached) | READ | 0.571 | 0.590 | 0.577 | 0.579 |
| R17: Merchant risk: refund rate per merchant (at least 30 payments) | READ | 22.161 | 21.994 | 22.001 | 22.052 |
| R18: Compliance: users without verified KYC who have successfully sent ₹10,000+ in total | READ | 43.685 | 44.160 | 43.000 | 43.615 |
| R19: Merchant report: last payment time and successful payment count of every verified Bengaluru merchant | READ | 8290.232 | 8342.709 | 8270.024 | 8300.988 |
| R20: Platform health: daily success rate in June 2026 | READ | 20.132 | 19.905 | 20.318 | 20.118 |
| R21: "Search businesses": merchants with "chai" in their name | READ | 2.180 | 2.359 | 2.189 | 2.243 |
| R22: Payment screen: user 15177's primary bank account and all their UPI IDs | READ | 7.885 | 8.033 | 8.056 | 7.991 |
| R23: Operations console: all transactions, newest first, page 8,001 (25 per page) | READ | 122.398 | 127.380 | 124.157 | 124.645 |
| R24: Customer support: find a payment by its UPI reference number | READ | 0.057 | 0.069 | 0.056 | 0.061 |
| R25: Bank health: average seconds from initiation to completion per payer bank (June 2026) | READ | 39.423 | 39.675 | 39.119 | 39.406 |
| W01: Pay: user 15177 starts a ₹250 payment to merchant 2 (PENDING until the bank confirms) | WRITE | 1.013 | 0.944 | 0.883 | 0.947 |
| W02: Bank callback: mark the oldest PENDING payment as successful | WRITE | 39.584 | 40.819 | 39.905 | 40.103 |
| W03: Scratch card: user 15177 scratches their oldest unscratched card | WRITE | 3.005 | 2.940 | 2.998 | 2.981 |
| W04: Nightly job (run at 00:00 on 4 Jul 2026): expire every reward whose time is up | WRITE | 3.793 | 3.734 | 3.549 | 3.692 |
| W05: Nightly job: bills past their due date and still unpaid become OVERDUE | WRITE | 3.962 | 3.916 | 3.869 | 3.916 |
| **Total (sum of all 30)** | | **9632.429** | **9664.020** | **9589.921** | **9628.792** |

#### Scan Types and Plan Analysis per Query

- **R01** (`Seq Scan on transactions | Seq Scan on vpas`, 28.823 ms): Slow for a real-time user screen because `vpas` has no index on `user_id` (requiring two sequential scans of 53,333 rows) and `transactions` has no indexes on `payer_vpa` or `payee_vpa` (forcing a Parallel Seq Scan over 250,468 rows with an `OR` condition).
- **R02** (`Index Scan using vpas_pkey on vpas | Index Scan using users_pkey on users`, 0.068 ms): Very fast because both the `WHERE v.vpa = ...` lookup and the join on `u.user_id = v.user_id` use primary key B-tree indexes (`vpas_pkey` and `users_pkey`).
- **R03** (`Seq Scan on transactions | Seq Scan on vpas`, 22.437 ms): Slow for a per-payment limit check because `vpas(user_id)` and `transactions(payer_vpa, initiated_at)` are unindexed, and applying `DATE(t.initiated_at)` prevents index range scans on `initiated_at`.
- **R04** (`Seq Scan on transactions`, 14.184 ms): Scans all 250,468 rows of `transactions` via a Parallel Seq Scan to find 120 `PENDING` rows because there is no index (or partial index) on `(status, initiated_at)`.
- **R05** (`Seq Scan on transactions`, 12.511 ms): Scans all 250,468 rows of `transactions` via a Parallel Seq Scan to return just 3 matching rows for `merchant_id = 2` on 29 June 2026 because `merchant_id` and `initiated_at` are unindexed.
- **R06** (`Seq Scan on transactions | Index Scan using merchants_pkey on merchants`, 12.729 ms): Performs a Parallel Seq Scan over all 250,468 `transactions` rows to filter one day of `SUCCESS` payments before merge-joining with `merchants_pkey`.
- **R07** (`Seq Scan on transactions | Index Scan using vpas_pkey on vpas | Index Scan using bank_accounts_pkey on bank_accounts`, 13.476 ms): Uses `vpas_pkey` and `bank_accounts_pkey` for the joins on the 135 failed payments, but still requires a full Parallel Seq Scan on `transactions` because `(status, initiated_at)` is unindexed.
- **R08** (`Seq Scan on transactions`, 251.740 ms): Slow because it sequentially scans 250,468 rows and performs an external merge disk sort (`6,912 kB` spilled to temp buffers) on 102,742 successful P2P rows to compute `GROUP BY payee_vpa, initiated_at::date` with `count(DISTINCT payer_vpa)`.
- **R09** (`Seq Scan on transactions`, 554.036 ms): Second-slowest query in the workload because it sequentially scans 250,468 rows and performs a large external merge disk sort (`18,712 kB` spilled to temp buffers) over 232,909 `SUCCESS` rows to compute the `lag(initiated_at) OVER (PARTITION BY payer_vpa, payee_vpa ORDER BY initiated_at)` window function.
- **R10** (`Seq Scan on rewards`, 2.939 ms): Sequentially scans all 39,799 rows in `rewards` to return 2 rows for `user_id = 15177` because there is no index on `(user_id, status, expires_at)`.
- **R11** (`Seq Scan on rewards`, 3.286 ms): Sequentially scans all 39,799 rows in `rewards` to find 51 unscratched expiring rewards because `(status, expires_at)` is unindexed.
- **R12** (`Seq Scan on bill_payments`, 2.315 ms): Sequentially scans all 30,000 rows in `bill_payments` to return 1 row for `user_id = 1072` because `(user_id, status, due_date)` is unindexed.
- **R13** (`Seq Scan on merchants | Seq Scan on transactions`, 46.331 ms): Scans all 250,468 `transactions` rows into a hashed SubPlan and scans 3,000 `merchants` rows, returning **0 rows** because `NOT IN (SELECT t.merchant_id FROM transactions t)` evaluates to `UNKNOWN` whenever `transactions.merchant_id` contains `NULL` (which is true for all P2P transactions).
- **R14** (`Seq Scan on transactions | Seq Scan on vpas | Index Scan using merchants_pkey on merchants`, 32.723 ms): Sequentially scans both `vpas` (53,333 rows) and `transactions` (250,468 rows) because `vpas(user_id)` and `transactions(payer_vpa)` are unindexed, using an index scan only for the final `merchants_pkey` lookup.
- **R15** (`Seq Scan on transactions | Seq Scan on merchants`, 17.857 ms): Performs a Parallel Seq Scan on `transactions` and a Seq Scan on `merchants` followed by hash aggregation and window ranking (`RANK() OVER (PARTITION BY m.city_id ...)`).
- **R16** (`Seq Scan on disputes | Index Scan using transactions_pkey on transactions`, 0.579 ms): Fast on seed data because `disputes` has only 3,569 rows (46 buffers) and the 75 open disputes join to `transactions` via `transactions_pkey`.
- **R17** (`Seq Scan on transactions`, 22.052 ms): Performs a Parallel Seq Scan and hash aggregation over all 139,887 `P2M` rows in `transactions` to compute per-merchant refund percentages.
- **R18** (`Seq Scan on transactions | Seq Scan on vpas | Seq Scan on users`, 43.615 ms): Sequentially scans all three tables (`users`, `vpas`, and `transactions`) and hash-joins them to aggregate total amount sent by unverified KYC users.
- **R19** (`Seq Scan on merchants | Seq Scan on transactions`, 8300.988 ms): **Slowest query in the workload (~8.3 seconds)** because it executes two correlated subqueries (`SubPlan 1` and `SubPlan 2`), each performing a full sequential scan of all 250,468 `transactions` rows for every single one of the 239 verified Bengaluru merchants ($239 \times 2 = 478$ full table scans of `transactions`, touching 2,206,486 shared buffers).
- **R20** (`Seq Scan on transactions`, 20.118 ms): Performs a Parallel Seq Scan over all 250,468 rows of `transactions` because filtering on `initiated_at::date` without an index scans the entire table to aggregate June 2026 daily success rates.
- **R21** (`Seq Scan on merchants`, 2.243 ms): Sequentially scans all 3,000 `merchants` rows applying `ILIKE '%chai%'` and sorts 300 matching rows because there is no trigram (`pg_trgm` GIN) index on `merchant_name`.
- **R22** (`Seq Scan on vpas | Seq Scan on bank_accounts`, 7.991 ms): Sequentially scans all 53,333 rows of `bank_accounts` and all 53,333 rows of `vpas` to return 2 rows for `user_id = 15177` because neither `bank_accounts(user_id)` nor `vpas(account_id)` is indexed.
- **R23** (`Seq Scan on transactions`, 124.645 ms): Slow because `ORDER BY initiated_at DESC OFFSET 200000 LIMIT 25` without an index on `initiated_at` forces a full sequential scan of 250,468 rows and an external merge disk sort (`14,256 kB` spilled to disk) to discard the first 200,000 rows.
- **R24** (`Index Scan using transactions_upi_ref_key on transactions`, 0.061 ms): Fastest query in the workload because `upi_ref` has a `UNIQUE` constraint, allowing a single B-tree index lookup via `transactions_upi_ref_key` touching only 4 buffers.
- **R25** (`Seq Scan on transactions | Seq Scan on vpas | Seq Scan on bank_accounts`, 39.406 ms): Sequentially scans `transactions` (Parallel Seq Scan), `vpas` (53,333 rows), and `bank_accounts` (53,333 rows) to hash-join and aggregate June 2026 completion latency per payer bank.
- **W01** (`(no scan)`, 0.947 ms): Single-row `INSERT INTO transactions` that maintains `transactions_pkey` and `transactions_upi_ref_key` and checks foreign keys on `vpas(vpa)` and `merchants(merchant_id)` via their primary key indexes.
- **W02** (`Index Scan using transactions_pkey on transactions`, 40.103 ms): Slow for a single-row update because `SELECT min(txn_id) FROM transactions WHERE status = 'PENDING'` walks `transactions_pkey` in ascending order, scanning and filtering out 249,875 non-`PENDING` rows (5,239 buffers) before finding the first `PENDING` transaction.
- **W03** (`Seq Scan on rewards | Index Scan using rewards_pkey on rewards`, 2.981 ms): Sequentially scans all 39,799 rows of `rewards` in `InitPlan 1` to find `min(reward_id)` for `user_id = 15177 AND status = 'UNSCRATCHED'`, then updates the single row via `rewards_pkey`.
- **W04** (`Seq Scan on rewards`, 3.692 ms): Sequentially scans all 39,799 rows of `rewards` to find and update 51 expired `UNSCRATCHED` rows because `(status, expires_at)` is unindexed.
- **W05** (`Seq Scan on bill_payments`, 3.916 ms): Sequentially scans all 30,000 rows of `bill_payments` to find and update 201 overdue `DUE` bills because `(status, due_date)` is unindexed.

---

### 5. Summary

- **Total queries benchmarked:** 30 (25 `READ` queries `R01`–`R25`, 5 `WRITE` queries `W01`–`W05`)
- **Number of runs per query:** 3
- **Total measured executions:** 90 (30 queries × 3 runs)
- **Total successful measurements:** 90
- **Total failed measurements:** 0
- **Sum of execution times across all 30 queries:**
  - **Run 1 total:** `9632.429 ms`
  - **Run 2 total:** `9664.020 ms`
  - **Run 3 total:** `9589.921 ms`
  - **Sum of 30 query averages:** `9628.792 ms` (`9.629 seconds`)
- **Overall average execution time per query:** `320.960 ms` (`9628.792 ms / 30`)

#### Notable Observations from Actual Measurements

1. **Correlated Subqueries Dominate Total Runtime (`R19`):** `R19` alone averages `8300.988 ms` (`86.21%` of the total `9628.792 ms` workload runtime) because PostgreSQL executes two unindexed sequential scans of `transactions` per verified Bengaluru merchant ($239 \times 2 = 478$ sequential scans of 250,468 rows).
2. **External Disk Sorts on Unindexed Analytical Queries (`R09`, `R08`, `R23`):**
   - `R09` (`554.036 ms` average) spills `18,712 kB` to disk sorting 232,909 rows for the `lag()` window function.
   - `R08` (`251.740 ms` average) spills `6,912 kB` to disk sorting 102,742 rows for `count(DISTINCT payer_vpa)`.
   - `R23` (`124.645 ms` average) spills `14,256 kB` to disk sorting all 250,468 rows for `OFFSET 200000 LIMIT 25`.
3. **Sub-millisecond Lookups Where Primary/Unique Keys Exist (`R24`, `R02`):** Queries that filter directly on columns backed by `PRIMARY KEY` or `UNIQUE` constraints—`R24` (`0.061 ms` via `transactions_upi_ref_key`) and `R02` (`0.068 ms` via `vpas_pkey` and `users_pkey`)—complete in under `0.1 ms`.
4. **Slow Ordered Index Walk Without Status Index (`W02`):** Although `W02` (`40.103 ms` average) uses `Index Scan using transactions_pkey`, it has to walk almost the entire primary key index (removing 249,875 rows by filter) because `PENDING` transactions reside near the end of `txn_id` order and there is no partial/composite index on `status`.
5. **Semantic NULL Issue in `R13` (`46.331 ms` average):** `R13` executes without SQL error in `46.331 ms`, but returns 0 rows because `WHERE m.merchant_id NOT IN (SELECT t.merchant_id FROM transactions t)` compares against `NULL` values present in `transactions.merchant_id` for P2P transactions.

---

### 6. Reproducibility

To reproduce these baseline timings from a clean clone of the repository:

1. **Unzip the seed dataset:**
   ```bash
   unzip -q -o seed_data.zip
   ```
2. **Create the `gpay` database, `gpay` schema, and baseline tables (`sql/01_schema.sql`):**
   ```bash
   psql -d postgres -c "CREATE DATABASE gpay;" -c "ALTER DATABASE gpay SET search_path TO gpay, public;"
   psql -d gpay -v ON_ERROR_STOP=1 -c "CREATE SCHEMA gpay;" -f sql/01_schema.sql
   ```
3. **Load all 9 CSV seed files (`sql/02_load_data.sql`) and update planner statistics (`ANALYZE`):**
   ```bash
   cd seed_data && psql -d gpay -v ON_ERROR_STOP=1 -f ../sql/02_load_data.sql -c "ANALYZE;" && cd ..
   ```
4. **Run the official benchmark script (3 runs per query across all 30 queries):**
   ```bash
   ./benchmarks/run_benchmark.sh gpay baseline
   ```
   *(Note: If using `Postgres.app` on macOS where `psql` is not in the default `PATH`, prefix with `PATH="/Applications/Postgres.app/Contents/Versions/latest/bin:$PATH"`.)*

This generates `benchmarks/results/baseline/summary.csv` and the 30 raw `EXPLAIN (ANALYZE, BUFFERS)` plan files (`benchmarks/results/baseline/R01.txt` through `benchmarks/results/baseline/W05.txt`).
