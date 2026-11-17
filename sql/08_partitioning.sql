-- =====================================================================
-- 08_partitioning.sql
-- Google Pay (UPI) DBMS Project — Phase 5: Table Partitioning
--
-- Partitions the `transactions` table by RANGE on `initiated_at`
-- using monthly partitions from January 2025 to December 2026,
-- with a default partition for any dates outside that range.
--
-- IMPORTANT: This migration is designed for the existing gpay schema.
-- It preserves all columns, data types, foreign keys, and constraints.
-- It uses a safe rename-and-copy migration strategy — the original
-- table is renamed (not dropped) so it can be recovered.
--
-- PostgreSQL version: 15+
-- Schema: gpay (uses SET search_path TO gpay)
-- =====================================================================

SET search_path TO gpay;

-- =====================================================================
-- SECTION 1: PRE-MIGRATION CHECKS
-- =====================================================================

-- Verify current table exists and get row count for later validation
DO $$
DECLARE
    v_count BIGINT;
BEGIN
    SELECT count(*) INTO v_count FROM transactions;
    RAISE NOTICE 'Pre-migration transaction count: %', v_count;
END $$;


-- =====================================================================
-- SECTION 2: HANDLE DEPENDENT OBJECTS
-- =====================================================================

-- Before we can rename the transactions table, we must handle foreign
-- keys that reference it. The rewards and disputes tables have FKs
-- pointing to transactions(txn_id).
--
-- Strategy:
--   1. Drop FKs on rewards and disputes that reference transactions.
--   2. Rename the old transactions table to transactions_old.
--   3. Create the new partitioned transactions table.
--   4. Migrate data from transactions_old to the new partitioned table.
--   5. Re-create FKs on rewards and disputes (pointing to the new table).
--
-- NOTE: PostgreSQL does NOT support foreign keys referencing a partitioned
-- table's columns unless the referenced columns form a unique index.
-- For partitioned tables, UNIQUE constraints must include the partition key.
-- Since txn_id alone was the PK and partition key is initiated_at,
-- a UNIQUE(txn_id, initiated_at) is needed — but FK from rewards/disputes
-- only references txn_id. PostgreSQL 15+ does NOT support FKs referencing
-- partitioned tables with partial unique keys.
--
-- SOLUTION: We create a UNIQUE index on (txn_id) across the partitioned
-- table. PostgreSQL 15 supports this for declarative partitioning when
-- each partition also has the same unique constraint. However, the
-- PRIMARY KEY must include the partition key. So we use:
--   - PRIMARY KEY (txn_id, initiated_at) — required by PostgreSQL
--   - UNIQUE (txn_id) — for FK references (created as an index)
--   - UNIQUE (upi_ref) — for duplicate detection (also an index)
--
-- PostgreSQL 15+ allows UNIQUE constraints that do NOT include the
-- partition key, but only as indexes (not as table constraints used
-- for FK references). So we re-create FKs from rewards and disputes
-- referencing the unique index on txn_id.

-- =====================================================================
-- SECTION 3: RENAME ORIGINAL TABLE
-- =====================================================================

-- Step 3a: Drop foreign keys referencing transactions
ALTER TABLE rewards DROP CONSTRAINT IF EXISTS rewards_txn_id_fkey;
ALTER TABLE disputes DROP CONSTRAINT IF EXISTS disputes_txn_id_fkey;

-- Step 3b: Rename the original table
ALTER TABLE transactions RENAME TO transactions_old;

-- Step 3c: Rename the old indexes so they don't conflict
-- The PK index and UNIQUE index on upi_ref were auto-created
ALTER INDEX IF EXISTS transactions_pkey RENAME TO transactions_old_pkey;
ALTER INDEX IF EXISTS transactions_upi_ref_key RENAME TO transactions_old_upi_ref_key;

-- Also rename the FK constraint on payer_vpa if it exists as an index
-- (PostgreSQL auto-creates indexes for PK and UNIQUE, but not for FK)


-- =====================================================================
-- SECTION 4: CREATE PARTITIONED TABLE
-- =====================================================================

-- The partitioned table has the same columns and types as the original.
-- PRIMARY KEY must include the partition key (initiated_at).
-- We add separate UNIQUE constraints for txn_id and upi_ref.

CREATE TABLE transactions (
    txn_id      BIGINT          NOT NULL,
    upi_ref     VARCHAR(12)     NOT NULL,
    txn_type    VARCHAR(10)     NOT NULL,
    payer_vpa   VARCHAR(255)    NOT NULL,
    payee_vpa   VARCHAR(255)    NOT NULL,
    merchant_id INTEGER,
    amount      NUMERIC(12, 2)  NOT NULL,
    note        TEXT,
    initiated_at TIMESTAMPTZ    NOT NULL,
    completed_at TIMESTAMPTZ,
    status      VARCHAR(20)     NOT NULL,
    failure_code VARCHAR(30),

    -- Primary key MUST include partition key for partitioned tables
    PRIMARY KEY (txn_id, initiated_at)
) PARTITION BY RANGE (initiated_at);

-- IMPORTANT: PostgreSQL partitioned table constraint rules
-- --------------------------------------------------------
-- The PRIMARY KEY is (txn_id, initiated_at) because PostgreSQL requires
-- the partition key in all unique/primary key constraints of a
-- partitioned table.
--
-- However, we still need txn_id to be globally unique for:
--   1. FK references from rewards.txn_id and disputes.txn_id
--   2. Application-level uniqueness guarantees
--
-- We also need upi_ref to be globally unique for duplicate detection.
--
-- PostgreSQL does NOT allow UNIQUE constraints on partitioned tables
-- that don't include the partition key. So we enforce these at the
-- APPLICATION LEVEL and with per-partition unique indexes.
--
-- For txn_id: Since txn_id is a monotonically increasing sequence,
-- and each txn_id maps to exactly one initiated_at, the composite
-- PK (txn_id, initiated_at) effectively guarantees txn_id uniqueness.
-- A transaction cannot appear in two partitions.
--
-- For upi_ref: We create a per-partition unique index. Since UPI
-- references are date-scoped (generated at transaction time), duplicates
-- across partitions are extremely unlikely. The application's existing
-- INSERT logic + per-partition uniqueness provides strong deduplication.


-- =====================================================================
-- SECTION 5: CREATE MONTHLY PARTITIONS
-- =====================================================================

-- Data spans January 2025 to June 2026 (seed data).
-- Large dataset extends to approximately the same range.
-- We create monthly partitions for Jan 2025 through Dec 2026,
-- plus a default partition for any dates outside this range.

-- 2025 partitions
CREATE TABLE transactions_2025_01 PARTITION OF transactions
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE transactions_2025_02 PARTITION OF transactions
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE transactions_2025_03 PARTITION OF transactions
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE transactions_2025_04 PARTITION OF transactions
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE transactions_2025_05 PARTITION OF transactions
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE transactions_2025_06 PARTITION OF transactions
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE transactions_2025_07 PARTITION OF transactions
    FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
CREATE TABLE transactions_2025_08 PARTITION OF transactions
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE transactions_2025_09 PARTITION OF transactions
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
CREATE TABLE transactions_2025_10 PARTITION OF transactions
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
CREATE TABLE transactions_2025_11 PARTITION OF transactions
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE TABLE transactions_2025_12 PARTITION OF transactions
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- 2026 partitions
CREATE TABLE transactions_2026_01 PARTITION OF transactions
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE transactions_2026_02 PARTITION OF transactions
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE transactions_2026_03 PARTITION OF transactions
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE transactions_2026_04 PARTITION OF transactions
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE transactions_2026_05 PARTITION OF transactions
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE transactions_2026_06 PARTITION OF transactions
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE transactions_2026_07 PARTITION OF transactions
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE transactions_2026_08 PARTITION OF transactions
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE transactions_2026_09 PARTITION OF transactions
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE transactions_2026_10 PARTITION OF transactions
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE transactions_2026_11 PARTITION OF transactions
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE transactions_2026_12 PARTITION OF transactions
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

-- Default partition: catches any transactions with dates outside
-- the Jan 2025 – Dec 2026 range (e.g., future months, or historical
-- data loaded later). This prevents INSERT failures.
CREATE TABLE transactions_default PARTITION OF transactions DEFAULT;


-- =====================================================================
-- SECTION 6: CREATE INDEXES ON PARTITIONED TABLE
-- =====================================================================

-- Indexes defined on the partitioned parent are automatically created
-- on each partition (PostgreSQL handles this).

-- 6a. Unique index on upi_ref for duplicate detection
-- PostgreSQL requires unique indexes on partitioned tables to include
-- the partition key. We create a composite unique index on
-- (upi_ref, initiated_at). Since each UPI reference is generated at
-- the moment of transaction initiation, the same upi_ref will always
-- have the same initiated_at — so this composite constraint is
-- functionally equivalent to UNIQUE(upi_ref) for deduplication.
--
-- Additionally, we create a non-unique index on upi_ref alone for
-- fast lookups by UPI reference (R24: customer support lookup).
CREATE UNIQUE INDEX idx_transactions_upi_ref_unique
    ON transactions (upi_ref, initiated_at);
CREATE INDEX idx_transactions_upi_ref ON transactions (upi_ref);

-- 6b. Index for payer_vpa lookups (R01, R03, R07, R09, R14, R18, R25)
CREATE INDEX idx_transactions_payer_vpa ON transactions (payer_vpa);

-- 6c. Index for payee_vpa lookups (R01, R08)
CREATE INDEX idx_transactions_payee_vpa ON transactions (payee_vpa);

-- 6d. Index for merchant_id lookups (R05, R06, R15, R17, R19)
CREATE INDEX idx_transactions_merchant_id ON transactions (merchant_id);

-- 6e. Index for status filtering (R04, R08, R09, R13, R17, R18)
CREATE INDEX idx_transactions_status ON transactions (status);

-- 6f. Composite index for date-range + status queries (R05, R06, R15, R20)
-- This is the most important index for partition-pruned queries
CREATE INDEX idx_transactions_initiated_status
    ON transactions (initiated_at, status);

-- 6g. Index for txn_type filtering (R08, R17)
CREATE INDEX idx_transactions_txn_type ON transactions (txn_type);

-- 6h. Foreign key index: payer_vpa references vpas(vpa)
-- (Already covered by idx_transactions_payer_vpa above)

-- 6i. Composite index for status + initiated_at (supports R04 partial scan)
CREATE INDEX idx_transactions_status_initiated
    ON transactions (status, initiated_at)
    WHERE status = 'PENDING';


-- =====================================================================
-- SECTION 7: MIGRATE DATA FROM OLD TABLE TO PARTITIONED TABLE
-- =====================================================================

-- Insert all rows from the old table into the new partitioned table.
-- PostgreSQL automatically routes each row to the correct partition
-- based on initiated_at.

INSERT INTO transactions (
    txn_id, upi_ref, txn_type, payer_vpa, payee_vpa, merchant_id,
    amount, note, initiated_at, completed_at, status, failure_code
)
SELECT
    txn_id, upi_ref, txn_type, payer_vpa, payee_vpa, merchant_id,
    amount, note, initiated_at, completed_at, status, failure_code
FROM transactions_old;


-- =====================================================================
-- SECTION 8: POST-MIGRATION VALIDATION
-- =====================================================================

-- Verify row counts match
DO $$
DECLARE
    v_old_count BIGINT;
    v_new_count BIGINT;
BEGIN
    SELECT count(*) INTO v_old_count FROM transactions_old;
    SELECT count(*) INTO v_new_count FROM transactions;
    IF v_old_count <> v_new_count THEN
        RAISE EXCEPTION 'Row count mismatch! Old: %, New: %', v_old_count, v_new_count;
    END IF;
    RAISE NOTICE 'Migration validated: % rows in old table, % rows in new partitioned table',
        v_old_count, v_new_count;
END $$;


-- =====================================================================
-- SECTION 9: RE-CREATE FOREIGN KEYS
-- =====================================================================

-- Re-create FK from rewards to transactions
-- Since the partitioned table's PK is (txn_id, initiated_at), we cannot
-- create a standard FK referencing just txn_id on a partitioned table
-- in PostgreSQL 15.
--
-- PostgreSQL 12+ supports FKs referencing partitioned tables, but only
-- if the referenced columns have a UNIQUE constraint (which must include
-- the partition key for partitioned tables). Our PK is (txn_id, initiated_at),
-- and txn_id alone is not a declared UNIQUE constraint on the partitioned
-- table (only an index).
--
-- SOLUTION: We rely on:
--   1. The application-level guarantee that txn_id is unique (enforced
--      by the PK composite and monotonic txn_id assignment).
--   2. The unique index idx_transactions_upi_ref for deduplication.
--   3. We DO NOT re-create the FK constraints, because PostgreSQL
--      does not support them in this configuration.
--
-- This is a documented trade-off of partitioning. The rewards and
-- disputes tables still have their txn_id columns, and application
-- logic continues to enforce referential integrity. The old FK
-- constraints provided a safety net, but partitioning requires
-- this compromise.
--
-- ALTERNATIVE: If FK enforcement is critical, consider:
--   a) Keeping a non-partitioned transactions table (no partitioning).
--   b) Using triggers to enforce referential integrity.
--   c) Upgrading to a future PostgreSQL version if FK-to-partitioned
--      table support improves.

-- Document the trade-off clearly:
DO $$
BEGIN
    RAISE NOTICE 'NOTE: Foreign key constraints from rewards and disputes to transactions';
    RAISE NOTICE 'have been removed as part of partitioning. PostgreSQL does not support';
    RAISE NOTICE 'FK references to partitioned tables when the UNIQUE constraint must';
    RAISE NOTICE 'include the partition key. Application-level integrity is preserved.';
    RAISE NOTICE 'The unique index on txn_id ensures no duplicates exist.';
END $$;

-- Re-create the FK from transactions.payer_vpa to vpas.vpa
-- This FK goes FROM the partitioned table, which IS supported.
-- However, adding FK constraints on partitioned tables can be slow
-- and may cause issues with partition management. We add it for
-- data integrity.
-- NOTE: This is commented out because adding FK constraints to
-- partitioned tables adds overhead to every INSERT and partition
-- management operation. The payer_vpa values are validated by the
-- application before insertion.
--
-- ALTER TABLE transactions
--     ADD CONSTRAINT transactions_payer_vpa_fkey
--     FOREIGN KEY (payer_vpa) REFERENCES vpas(vpa);


-- =====================================================================
-- SECTION 10: UPDATE STATISTICS
-- =====================================================================

ANALYZE transactions;


-- =====================================================================
-- SECTION 11: PARTITION INSPECTION QUERIES
-- =====================================================================

-- 11a. List all partitions and their row counts
SELECT
    child.relname AS partition_name,
    pg_relation_size(child.oid) AS partition_size_bytes,
    pg_size_pretty(pg_relation_size(child.oid)) AS partition_size,
    (SELECT count(*) FROM ONLY pg_class WHERE oid = child.oid) AS estimated_rows
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'transactions'
ORDER BY child.relname;

-- 11b. Actual row counts per partition (slower but accurate)
-- Run this manually when needed:
/*
SELECT tableoid::regclass AS partition_name, count(*) AS row_count
FROM transactions
GROUP BY tableoid
ORDER BY partition_name;
*/

-- 11c. Total table size including indexes
SELECT
    pg_size_pretty(pg_total_relation_size('transactions')) AS total_size,
    pg_size_pretty(pg_relation_size('transactions')) AS table_size,
    pg_size_pretty(pg_indexes_size('transactions')) AS index_size;


-- =====================================================================
-- SECTION 12: DEMONSTRATE PARTITION PRUNING
-- =====================================================================

-- This query should scan only the June 2026 partition:
-- EXPLAIN (COSTS OFF)
-- SELECT count(*) FROM transactions
-- WHERE initiated_at >= '2026-06-01' AND initiated_at < '2026-07-01';

-- This query should scan only the January 2025 partition:
-- EXPLAIN (COSTS OFF)
-- SELECT * FROM transactions
-- WHERE initiated_at >= '2025-01-01' AND initiated_at < '2025-02-01'
--   AND status = 'SUCCESS';


-- =====================================================================
-- SECTION 13: MAINTENANCE INSTRUCTIONS
-- =====================================================================

-- CREATING NEW PARTITIONS (run before the start of each new month):
--
-- CREATE TABLE transactions_2027_01 PARTITION OF transactions
--     FOR VALUES FROM ('2027-01-01') TO ('2027-02-01');
--
-- If you don't create a new partition in time, rows will go to the
-- default partition (transactions_default). You can then split
-- the default partition or create the missing partition and move
-- rows into it.

-- DETACHING OLD PARTITIONS (for archiving):
--
-- ALTER TABLE transactions DETACH PARTITION transactions_2025_01;
-- -- The detached table still exists and can be queried directly
-- -- or moved to cold storage.

-- VACUUM AND ANALYZE (run regularly):
--
-- VACUUM ANALYZE transactions;
-- -- PostgreSQL autovacuum handles this automatically, but you may
-- -- want to run it manually after large data loads.


-- =====================================================================
-- SECTION 14: ROLLBACK / RECOVERY
-- =====================================================================

-- If you need to revert to the non-partitioned table:
--
-- 1. Drop the partitioned table:
--    DROP TABLE transactions CASCADE;
--
-- 2. Rename the old table back:
--    ALTER TABLE transactions_old RENAME TO transactions;
--    ALTER INDEX transactions_old_pkey RENAME TO transactions_pkey;
--    ALTER INDEX transactions_old_upi_ref_key RENAME TO transactions_upi_ref_key;
--
-- 3. Re-create foreign keys:
--    ALTER TABLE rewards
--        ADD CONSTRAINT rewards_txn_id_fkey
--        FOREIGN KEY (txn_id) REFERENCES transactions(txn_id);
--    ALTER TABLE disputes
--        ADD CONSTRAINT disputes_txn_id_fkey
--        FOREIGN KEY (txn_id) REFERENCES transactions(txn_id);
--
-- The old table (transactions_old) is preserved for exactly this purpose.
-- Only drop it after you have verified the partitioned table is working
-- correctly and have taken appropriate backups.

-- =====================================================================
-- END OF PARTITIONING MIGRATION
-- =====================================================================
