SET search_path TO gpay;

-- Support the VPA lookup / user-identity path used by R02 and by R01/R03/R14/R18.
-- Filtering by v.user_id and then matching the VPA is a classic lookup pattern; putting
-- user_id first keeps all rows for one user compact and the second key (vpa) lets the
-- planner quickly reach the correct record without scanning the whole vpas table.
-- Expected impact: much faster VPA existence checks and user transaction lookups.
-- Trade-off: extra index storage and a small write penalty when inserting or updating VPAs.
CREATE INDEX IF NOT EXISTS idx_vpas_user_id_vpa
    ON vpas (user_id, vpa);

-- Support the exact VPA lookup used by payment validation and payer/payee joins.
-- The vpa column is unique as the primary key, but with the additional active-status filter
-- the index still helps when PostgreSQL has to join through the VPA identity to user data.
-- Expected impact: faster R02 validation checks and reduced random reads in payer/payee joins.
-- Trade-off: a little more disk use; updates to vpa or activity flags pay this cost.
CREATE INDEX IF NOT EXISTS idx_vpas_vpa_user_id_active
    ON vpas (vpa, user_id, is_active);

-- Support user-to-transaction lookups in R01, R03, R14 and R18: transactions are filtered by
-- payer_vpa, status and time range. The leading columns match the most selective predicates
-- in the workload, so the planner can seek the relevant transactions and then scan only that slice.
-- Expected impact: large reduction in rows scanned for per-user history and daily limit checks.
-- Trade-off: slower INSERT/UPDATE of transactions because every new payment adds an index entry.
CREATE INDEX IF NOT EXISTS idx_transactions_payer_status_time
    ON transactions (payer_vpa, status, initiated_at DESC);

-- Support payee-side history lookups in R01 and other receive-side queries.
-- Payee lookups are also filtered by status and recency, so the same shape as the payer-side
-- index preserves fast index-only or index-backed scans without widening the query too much.
-- Expected impact: faster receive-side history screens and P2P receive analytics.
-- Trade-off: additional write cost for every transaction insert; still justified for read-heavy flows.
CREATE INDEX IF NOT EXISTS idx_transactions_payee_status_time
    ON transactions (payee_vpa, status, initiated_at DESC);

-- Support status/time filters used by reconciliation, analytics and reporting queries.
-- The leading status column narrows the table to the relevant lifecycle buckets (SUCCESS, FAILED,
-- PENDING), while initiated_at keeps the rows ordered by time for dashboards and SLA checks.
-- Expected impact: noticeably faster date-range scans in R04, R05, R06, R07, R20 and similar queries.
-- Trade-off: more write overhead for transaction inserts and updates, with index maintenance on every status change.
CREATE INDEX IF NOT EXISTS idx_transactions_status_time
    ON transactions (status, initiated_at DESC);

-- Support merchant-driven collection and settlement queries in R05, R06, R15, R19.
-- Merchant_id is the natural join key; adding status and time allows PostgreSQL to find only
-- successful payments for a merchant within a date window without scanning unrelated rows.
-- Expected impact: substantially faster merchant rolls-ups, GMV reports and settlement queries.
-- Trade-off: index size grows with merchant activity; updates to merchant payment status cost more.
CREATE INDEX IF NOT EXISTS idx_transactions_merchant_status_time
    ON transactions (merchant_id, status, initiated_at DESC);

-- Support fraud and platform analytics that filter by txn_type, status and time.
-- These reports aggregate across large subsets of payments and benefit from looking at only the
-- relevant transaction type/status in time order rather than scanning the whole table.
-- Expected impact: faster fraud checks and daily platform health reports (R08, R09, R17, R20).
-- Trade-off: storage overhead for a broader index and slower writes in busy payment workloads.
CREATE INDEX IF NOT EXISTS idx_transactions_type_status_time
    ON transactions (txn_type, status, initiated_at DESC);

-- Support large scans ordered by recency for operations console and recent activity pages.
-- The ORDER BY initiated_at DESC pattern used in R23 benefits from a time-ordered index that
-- can satisfy the sort without a separate sort node when the planner can use the index scan.
-- Expected impact: faster newest-first lookups and pagination at the tail of the transaction table.
-- Trade-off: large index on a very active table increases storage footprint and affects insert latency.
CREATE INDEX IF NOT EXISTS idx_transactions_initiated_at_desc
    ON transactions (initiated_at DESC);

-- Support merchant search and verification filters used by business and success-team dashboards.
-- city_id and is_verified are the most common dimensions in merchant lists, so they are ordered
-- first to allow fast retrieval of verified merchants per city before joining other tables.
-- Expected impact: faster merchant listings, settlement views and location-based reports.
-- Trade-off: moderate index storage; merchant verification updates cost slightly more.
CREATE INDEX IF NOT EXISTS idx_merchants_city_verified
    ON merchants (city_id, is_verified);

-- Support merchant name searches and business search pages. The query pattern is a case-insensitive
-- contains search, which is not perfectly index-friendly, but a basic name index still helps for
-- narrower exact matches and keeps sort/order work manageable in bounded result sets.
-- Expected impact: better response for merchant search and list screens where a name filter is combined.
-- Trade-off: extra write cost for merchant name updates and index storage; content-search patterns remain
-- less selective than exact-match B-tree lookups.
CREATE INDEX IF NOT EXISTS idx_merchants_name
    ON merchants (merchant_name);

-- Support reward jobs and user reward retrieval in R10, R11 and related reward notifications.
-- The common access pattern is user_id + status + expiration, which narrows the result set before sort.
-- Expected impact: faster reward tabs and expiry notifications without scanning all rewards rows.
-- Trade-off: writes to rewards become slightly slower when status or expiry changes.
CREATE INDEX IF NOT EXISTS idx_rewards_user_status_expires
    ON rewards (user_id, status, expires_at);

-- Support automated reward expiry jobs that scan by status and expiration for all users.
-- This index keeps the time-based sweep compact and lets PostgreSQL avoid a full table scan for
-- the nightly job that marks expired cards.
-- Expected impact: more efficient nightly cleanup and early-expiry notifications.
-- Trade-off: extra storage and a write penalty during reward updates or creation batches.
CREATE INDEX IF NOT EXISTS idx_rewards_status_expires
    ON rewards (status, expires_at);

-- Support user bill reminders and due-date queries in R12 and nightly overdue processing.
-- The query filters by user_id, status and due_date together, so ordering by due_date first keeps
-- the relevant due bills clustered and avoids large scans across all bill records.
-- Expected impact: faster bill reminders and overdue sweeps for individual users and jobs.
-- Trade-off: index upkeep on bill insert/update workload and additional storage.
CREATE INDEX IF NOT EXISTS idx_bill_payments_user_status_due
    ON bill_payments (user_id, status, due_date);

-- Support dispute queue and SLA monitoring in R16.
-- The workload looks up disputes by status and age; ordering by raised_at means the planner can
-- return open cases breaching SLA quickly without sorting large volumes of disputes.
-- Expected impact: shorter breach detection and dispute queue responses.
-- Trade-off: slower dispute inserts/updates and extra storage in the dispute table.
CREATE INDEX IF NOT EXISTS idx_disputes_status_raised
    ON disputes (status, raised_at);

-- Support the transaction-to-dispute join and dispute lookups by transaction in support workflows.
-- This narrows the dispute result set quickly when a transaction is used to fetch or inspect disputes.
-- Expected impact: faster dispute history and transaction support checks.
-- Trade-off: modest index maintenance overhead when disputes are created or resolved.
CREATE INDEX IF NOT EXISTS idx_disputes_txn_id
    ON disputes (txn_id);

ANALYZE vpas;
ANALYZE transactions;
ANALYZE merchants;
ANALYZE rewards;
ANALYZE bill_payments;
ANALYZE disputes;
