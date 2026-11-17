#!/usr/bin/env python3
"""
Large-Scale Benchmark Script for Google Pay (UPI) DBMS Project — Phase 5
=========================================================================

This script generates synthetic transaction data at multiple scales and
benchmarks key query operations on both non-partitioned and partitioned
PostgreSQL configurations.

Usage:
    python3 benchmarks/scripts/generate_and_benchmark.py

Requirements:
    pip3 install psycopg2-binary (or psycopg2)

Environment:
    PostgreSQL running on localhost:5433 (Docker container gpay_postgres)
    User: gpay, Password: gpay123
    Databases: gpay_baseline (non-partitioned), gpay_partitioned (partitioned)
"""

import csv
import io
import os
import random
import time
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip3 install psycopg2-binary")
    sys.exit(1)

# =====================================================================
# Configuration
# =====================================================================

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'user': 'gpay',
    'password': 'gpay123',
}

BASELINE_DB = 'gpay_baseline'
PARTITIONED_DB = 'gpay_partitioned'

# Dataset sizes to benchmark
DATASET_SIZES = [10_000, 100_000, 500_000]

# Project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'benchmarks', 'results', 'large')
DATASETS_DIR = os.path.join(PROJECT_ROOT, 'benchmarks', 'datasets')

# Benchmark parameters
NUM_RUNS = 3  # Number of runs per query for averaging

# =====================================================================
# Synthetic Data Generator
# =====================================================================

# Realistic Indian merchant names, banks, etc.
MERCHANT_NAMES = [
    'Ganesh Store', 'Balaji Store', 'Krishna Textiles', 'Chai Point',
    'Dominos Pizza', 'Swiggy Food', 'Zomato Delivery', 'BigBasket',
    'Flipkart Online', 'Amazon India', 'Reliance Digital', 'DMart',
    'More Supermarket', 'Spencer', 'Star Bazaar', 'Croma',
    'Nykaa Beauty', 'Myntra Fashion', 'PharmEasy', 'Apollo Pharmacy',
    'IRCTC', 'MakeMyTrip', 'Ola Rides', 'Uber India', 'Rapido',
    'JioMart', 'Paytm Mall', 'Meesho', 'Lenskart', 'BoAt Audio',
]

BANK_NAMES = [
    'HDFC Bank', 'ICICI Bank', 'State Bank of India', 'Axis Bank',
    'Kotak Mahindra Bank', 'Punjab National Bank', 'Bank of Baroda',
    'Canara Bank', 'Union Bank', 'IndusInd Bank',
]

IFSC_PREFIXES = [
    'HDFC', 'ICIC', 'SBIN', 'UTIB', 'KKBK', 'PUNB', 'BARB',
    'CNRB', 'UBIN', 'INDB',
]

CITIES = [
    (1, 'Bengaluru', 'Karnataka'),
    (2, 'Mumbai', 'Maharashtra'),
    (3, 'Delhi', 'Delhi'),
    (4, 'Hyderabad', 'Telangana'),
    (5, 'Chennai', 'Tamil Nadu'),
    (6, 'Pune', 'Maharashtra'),
    (7, 'Kolkata', 'West Bengal'),
    (8, 'Ahmedabad', 'Gujarat'),
    (9, 'Jaipur', 'Rajasthan'),
    (10, 'Lucknow', 'Uttar Pradesh'),
]

VPA_SUFFIXES = ['@oksbi', '@okhdfcbank', '@okicici', '@okaxis', '@okbizaxis']

TXN_STATUSES = ['SUCCESS', 'FAILED', 'PENDING', 'REVERSED', 'REFUNDED']
TXN_STATUS_WEIGHTS = [0.85, 0.08, 0.02, 0.03, 0.02]

FAILURE_CODES = [
    'INSUFFICIENT_BALANCE', 'BANK_TIMEOUT', 'INVALID_VPA',
    'TRANSACTION_DECLINED', 'NETWORK_ERROR', 'EXCEEDS_LIMIT',
]

BILLER_CATEGORIES = ['ELECTRICITY', 'MOBILE', 'DTH', 'GAS', 'WATER', 'BROADBAND']
BILLER_NAMES = [
    'Tata Power', 'Adani Electricity', 'BSES', 'Jio', 'Airtel',
    'Vi', 'Tata Sky', 'Dish TV', 'Indane Gas', 'HP Gas',
    'Delhi Jal Board', 'BWSSB', 'ACT Fibernet', 'BSNL',
]

MCC_CODES = ['5411', '5812', '5912', '7832', '5311', '5651', '5999', '4121', '5944', '5691']

DISPUTE_REASONS = [
    'MONEY_DEBITED_NOT_CREDITED', 'FRAUD', 'DUPLICATE_TRANSACTION',
    'WRONG_AMOUNT', 'UNAUTHORIZED_TRANSACTION',
]

FIRST_NAMES = [
    'Aarav', 'Vivaan', 'Aditya', 'Aryan', 'Reyansh', 'Atharv', 'Vihaan',
    'Sai', 'Krishna', 'Dhruv', 'Kabir', 'Ananya', 'Priya', 'Sneha',
    'Ishita', 'Meera', 'Saanvi', 'Diya', 'Riya', 'Pooja', 'Tanvi',
    'Neha', 'Kavya', 'Shreya', 'Ritika',
]

LAST_NAMES = [
    'Sharma', 'Patel', 'Singh', 'Kumar', 'Gupta', 'Reddy', 'Joshi',
    'Banerjee', 'Nair', 'Iyer', 'Mehta', 'Shah', 'Verma', 'Malhotra',
    'Kapoor', 'Desai', 'Rao', 'Mishra', 'Pandey', 'Chopra',
]

IST = timezone(timedelta(hours=5, minutes=30))

# Date range for transactions
TXN_START_DATE = datetime(2025, 1, 1, tzinfo=IST)
TXN_END_DATE = datetime(2026, 6, 30, 23, 59, 59, tzinfo=IST)


def generate_synthetic_data(num_transactions):
    """Generate synthetic data for the given number of transactions."""
    print(f"\n--- Generating synthetic data for {num_transactions:,} transactions ---")
    
    # Scale other tables proportionally to the seed data ratios
    # Seed: 250,468 txns, 40,000 users, 53,333 accounts, 3,000 merchants
    scale = num_transactions / 250_468
    
    num_users = max(100, int(40_000 * scale))
    num_accounts = max(100, int(53_333 * scale))
    num_merchants = max(50, min(3000, int(3_000 * scale)))
    num_vpas = num_accounts  # 1:1 with accounts
    num_rewards = max(10, int(39_799 * scale))
    num_bills = max(10, int(30_000 * scale))
    num_disputes = max(5, int(3_569 * scale))
    
    print(f"  Users: {num_users:,}, Accounts: {num_accounts:,}, VPAs: {num_vpas:,}")
    print(f"  Merchants: {num_merchants:,}, Rewards: {num_rewards:,}")
    print(f"  Bills: {num_bills:,}, Disputes: {num_disputes:,}")
    
    data = {}
    
    # Cities (always 10)
    data['cities'] = CITIES
    
    # Users
    users = []
    for uid in range(1, num_users + 1):
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        full_name = f"{fname} {lname}"
        phone = f"9{uid:09d}"
        email = f"{fname.lower()}.{lname.lower()}{uid}@gmail.com" if random.random() > 0.15 else None
        city_id = random.randint(1, 10)
        kyc_status = random.choice(['VERIFIED', 'PENDING', 'REJECTED'])
        is_blocked = 't' if random.random() < 0.01 else 'f'
        created_at = TXN_START_DATE - timedelta(days=random.randint(30, 1800))
        users.append((uid, full_name, phone, email, city_id, kyc_status, is_blocked,
                      created_at.isoformat()))
    data['users'] = users
    
    # Bank accounts (at least 1 per user, some have 2)
    accounts = []
    user_accounts = {}  # user_id -> list of account_ids
    aid = 1
    for uid in range(1, num_users + 1):
        num_accts = 1 if random.random() > 0.3 else 2
        user_accounts[uid] = []
        for i in range(num_accts):
            if aid > num_accounts:
                break
            bank_idx = random.randint(0, len(BANK_NAMES) - 1)
            bank_name = BANK_NAMES[bank_idx]
            ifsc = f"{IFSC_PREFIXES[bank_idx]}000{random.randint(1000, 9999)}"
            last4 = f"{random.randint(1000, 9999)}"
            acct_type = 'SAVINGS' if random.random() > 0.1 else 'CURRENT'
            is_primary = 't' if i == 0 else 'f'
            linked_at = users[uid - 1][7]  # Same as user created_at
            accounts.append((aid, uid, bank_name, ifsc, last4, acct_type, is_primary, linked_at))
            user_accounts[uid].append(aid)
            aid += 1
    data['bank_accounts'] = accounts
    
    # VPAs (1 per account)
    vpas = []
    user_vpas = {}  # user_id -> list of vpas
    for account in accounts:
        aid_val, uid, bank_name, _, _, _, _, _ = account
        fname = users[uid - 1][1].split()[0].lower()
        lname = users[uid - 1][1].split()[-1].lower()
        suffix = random.choice(VPA_SUFFIXES)
        vpa = f"{fname}.{lname}{uid}{suffix}"
        is_active = 't' if random.random() > 0.05 else 'f'
        created_at = account[7]
        vpas.append((vpa, uid, aid_val, is_active, created_at))
        if uid not in user_vpas:
            user_vpas[uid] = []
        user_vpas[uid].append(vpa)
    data['vpas'] = vpas
    
    # Merchants
    merchants = []
    merchant_vpas = {}
    for mid in range(1, num_merchants + 1):
        mname = f"{random.choice(MERCHANT_NAMES)} {mid}"
        mcc = random.choice(MCC_CODES)
        mvpa = f"{mname.lower().replace(' ', '')}{mid}@okbizaxis"
        city_id = random.randint(1, 10)
        is_verified = 't' if random.random() > 0.1 else 'f'
        onboarded = (TXN_START_DATE - timedelta(days=random.randint(30, 2000))).strftime('%Y-%m-%d')
        merchants.append((mid, mname, mcc, mvpa, city_id, is_verified, onboarded))
        merchant_vpas[mid] = mvpa
    data['merchants'] = merchants
    
    # Transactions
    all_vpa_strings = [v[0] for v in vpas]
    transactions = []
    total_seconds = int((TXN_END_DATE - TXN_START_DATE).total_seconds())
    
    for txn_id in range(1, num_transactions + 1):
        upi_ref = f"{600000000000 + txn_id}"
        
        # 60% P2M, 40% P2P
        if random.random() < 0.6:
            txn_type = 'P2M'
            mid = random.randint(1, num_merchants)
            payee_vpa = merchant_vpas[mid]
        else:
            txn_type = 'P2P'
            mid = None
            payee_vpa = random.choice(all_vpa_strings)
        
        payer_vpa = random.choice(all_vpa_strings)
        # Avoid self-payment
        while payer_vpa == payee_vpa:
            payer_vpa = random.choice(all_vpa_strings)
        
        amount = round(random.uniform(1, 50000), 2)
        
        rand_seconds = random.randint(0, total_seconds)
        initiated_at = TXN_START_DATE + timedelta(seconds=rand_seconds)
        
        status = random.choices(TXN_STATUSES, weights=TXN_STATUS_WEIGHTS, k=1)[0]
        
        completed_at = None
        failure_code = None
        
        if status == 'SUCCESS':
            completed_at = initiated_at + timedelta(seconds=random.randint(1, 10))
        elif status == 'FAILED':
            failure_code = random.choice(FAILURE_CODES)
            completed_at = initiated_at + timedelta(seconds=random.randint(1, 30))
        elif status == 'REVERSED':
            completed_at = initiated_at + timedelta(seconds=random.randint(60, 3600))
        elif status == 'REFUNDED':
            completed_at = initiated_at + timedelta(days=random.randint(1, 7))
        # PENDING: no completed_at
        
        note = None  # Mostly empty, like the real data
        
        transactions.append((
            txn_id, upi_ref, txn_type, payer_vpa, payee_vpa,
            mid, f"{amount:.2f}", note,
            initiated_at.isoformat(),
            completed_at.isoformat() if completed_at else None,
            status, failure_code
        ))
    
    data['transactions'] = transactions
    
    # Rewards (linked to some transactions)
    rewards = []
    txn_ids_for_rewards = random.sample(range(1, num_transactions + 1), min(num_rewards, num_transactions))
    for rid, txn_id in enumerate(txn_ids_for_rewards, 1):
        txn = transactions[txn_id - 1]
        uid_vpa = txn[3]  # payer_vpa
        # Find user_id from VPA
        uid = None
        for v in vpas:
            if v[0] == uid_vpa:
                uid = v[1]
                break
        if uid is None:
            uid = random.randint(1, num_users)
        
        reward_type = random.choice(['CASHBACK', 'SCRATCH_CARD'])
        r_amount = round(random.uniform(5, 100), 2)
        r_status = random.choice(['CREDITED', 'UNSCRATCHED', 'EXPIRED'])
        issued_at = datetime.fromisoformat(txn[8])
        expires_at = issued_at + timedelta(days=30)
        credited_at = None
        if r_status == 'CREDITED':
            credited_at = issued_at + timedelta(hours=random.randint(1, 48))
        
        rewards.append((
            rid, uid, txn_id, reward_type, f"{r_amount:.2f}", r_status,
            issued_at.isoformat(), expires_at.isoformat(),
            credited_at.isoformat() if credited_at else None
        ))
    data['rewards'] = rewards
    
    # Bill payments
    bills = []
    for bid in range(1, num_bills + 1):
        uid = random.randint(1, num_users)
        cat = random.choice(BILLER_CATEGORIES)
        bname = random.choice(BILLER_NAMES)
        consumer_num = f"{random.randint(1000000000, 9999999999)}"
        b_amount = round(random.uniform(100, 10000), 2)
        due_date = (TXN_START_DATE + timedelta(days=random.randint(30, 600))).strftime('%Y-%m-%d')
        b_status = random.choice(['PAID', 'DUE', 'OVERDUE'])
        paid_at = None
        if b_status == 'PAID':
            paid_at = (datetime.strptime(due_date, '%Y-%m-%d').replace(tzinfo=IST) 
                      - timedelta(days=random.randint(0, 5))).isoformat()
        bills.append((bid, uid, cat, bname, consumer_num, f"{b_amount:.2f}", due_date, b_status, paid_at))
    data['bill_payments'] = bills
    
    # Disputes
    disputes = []
    txn_ids_for_disputes = random.sample(range(1, num_transactions + 1), min(num_disputes, num_transactions))
    for did, txn_id in enumerate(txn_ids_for_disputes, 1):
        txn = transactions[txn_id - 1]
        uid_vpa = txn[3]
        uid = None
        for v in vpas:
            if v[0] == uid_vpa:
                uid = v[1]
                break
        if uid is None:
            uid = random.randint(1, num_users)
        
        reason = random.choice(DISPUTE_REASONS)
        raised_at = datetime.fromisoformat(txn[8]) + timedelta(hours=random.randint(1, 72))
        d_status = random.choice(['OPEN', 'RESOLVED', 'REJECTED'])
        resolved_at = None
        if d_status in ('RESOLVED', 'REJECTED'):
            resolved_at = raised_at + timedelta(days=random.randint(1, 30))
        
        disputes.append((
            did, txn_id, uid, reason,
            raised_at.isoformat(), d_status,
            resolved_at.isoformat() if resolved_at else None
        ))
    data['disputes'] = disputes
    
    return data


def load_data_to_db(conn, data, schema='gpay'):
    """Load synthetic data into the given database connection."""
    cur = conn.cursor()
    cur.execute(f"SET search_path TO {schema};")
    
    # Clear existing data in reverse dependency order
    for table in ['disputes', 'rewards', 'bill_payments', 'transactions',
                  'merchants', 'vpas', 'bank_accounts', 'users', 'cities']:
        cur.execute(f"TRUNCATE {table} CASCADE;")
    
    # Load cities
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in data['cities']:
        writer.writerow(row)
    buf.seek(0)
    cur.copy_expert("COPY cities FROM STDIN WITH (FORMAT csv)", buf)
    
    # Load users
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in data['users']:
        writer.writerow([v if v is not None else '' for v in row])
    buf.seek(0)
    cur.copy_expert("COPY users FROM STDIN WITH (FORMAT csv, NULL '')", buf)
    
    # Load bank_accounts
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in data['bank_accounts']:
        writer.writerow(row)
    buf.seek(0)
    cur.copy_expert("COPY bank_accounts FROM STDIN WITH (FORMAT csv)", buf)
    
    # Load vpas
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in data['vpas']:
        writer.writerow(row)
    buf.seek(0)
    cur.copy_expert("COPY vpas FROM STDIN WITH (FORMAT csv)", buf)
    
    # Load merchants
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in data['merchants']:
        writer.writerow(row)
    buf.seek(0)
    cur.copy_expert("COPY merchants FROM STDIN WITH (FORMAT csv)", buf)
    
    # Load transactions
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in data['transactions']:
        writer.writerow([v if v is not None else '' for v in row])
    buf.seek(0)
    cur.copy_expert("COPY transactions FROM STDIN WITH (FORMAT csv, NULL '')", buf)
    
    # Load bill_payments
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in data['bill_payments']:
        writer.writerow([v if v is not None else '' for v in row])
    buf.seek(0)
    cur.copy_expert("COPY bill_payments FROM STDIN WITH (FORMAT csv, NULL '')", buf)
    
    # Load rewards
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in data['rewards']:
        writer.writerow([v if v is not None else '' for v in row])
    buf.seek(0)
    cur.copy_expert("COPY rewards FROM STDIN WITH (FORMAT csv, NULL '')", buf)
    
    # Load disputes
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in data['disputes']:
        writer.writerow([v if v is not None else '' for v in row])
    buf.seek(0)
    cur.copy_expert("COPY disputes FROM STDIN WITH (FORMAT csv, NULL '')", buf)
    
    conn.commit()
    
    # Run ANALYZE
    cur.execute("ANALYZE;")
    conn.commit()
    
    # Verify counts
    for table in ['cities', 'users', 'bank_accounts', 'vpas', 'merchants',
                  'transactions', 'bill_payments', 'rewards', 'disputes']:
        cur.execute(f"SELECT count(*) FROM {table};")
        count = cur.fetchone()[0]
        print(f"  {table}: {count:,} rows")
    
    cur.close()


# =====================================================================
# Benchmark Queries
# =====================================================================

BENCHMARK_QUERIES = {
    'user_txn_retrieval': {
        'name': 'User-specific transaction retrieval',
        'sql': """
            SELECT t.txn_id, t.upi_ref, t.payer_vpa, t.payee_vpa, t.amount, t.status, t.initiated_at
            FROM transactions t
            WHERE t.payer_vpa IN (SELECT vpa FROM vpas WHERE user_id = 1)
            ORDER BY t.initiated_at DESC
            LIMIT 30;
        """,
    },
    'date_range_filter': {
        'name': 'Date-range transaction filtering',
        'sql': """
            SELECT count(*), sum(amount)
            FROM transactions
            WHERE initiated_at >= '2026-06-01' AND initiated_at < '2026-07-01'
              AND status = 'SUCCESS';
        """,
    },
    'category_filter': {
        'name': 'Category-based filtering (P2M)',
        'sql': """
            SELECT merchant_id, count(*) AS payments,
                   round(100.0 * count(*) FILTER (WHERE status = 'REFUNDED') / count(*), 2) AS refund_pct
            FROM transactions
            WHERE txn_type = 'P2M'
            GROUP BY merchant_id
            HAVING count(*) >= 30
            ORDER BY refund_pct DESC
            LIMIT 20;
        """,
    },
    'monthly_aggregation': {
        'name': 'Monthly spending aggregation',
        'sql': """
            SELECT date_trunc('month', initiated_at) AS month,
                   count(*) AS payments, sum(amount) AS total
            FROM transactions
            WHERE status = 'SUCCESS'
            GROUP BY 1
            ORDER BY 1;
        """,
    },
    'dashboard_summary': {
        'name': 'Dashboard summary query',
        'sql': """
            SELECT
                count(*) AS total_txns,
                count(*) FILTER (WHERE status = 'SUCCESS') AS successful,
                count(*) FILTER (WHERE status = 'FAILED') AS failed,
                count(*) FILTER (WHERE status = 'PENDING') AS pending,
                sum(amount) FILTER (WHERE status = 'SUCCESS') AS total_success_amount,
                round(100.0 * count(*) FILTER (WHERE status = 'SUCCESS') / count(*), 2) AS success_rate
            FROM transactions;
        """,
    },
    'duplicate_detection': {
        'name': 'Duplicate transaction detection',
        'sql': """
            SELECT upi_ref, count(*)
            FROM transactions
            GROUP BY upi_ref
            HAVING count(*) > 1;
        """,
    },
    'top_merchants': {
        'name': 'Top merchants aggregation',
        'sql': """
            SELECT m.merchant_id, m.merchant_name, count(*) AS payments, sum(t.amount) AS gmv
            FROM transactions t
            JOIN merchants m ON m.merchant_id = t.merchant_id
            WHERE t.status = 'SUCCESS'
              AND t.initiated_at >= '2026-06-01' AND t.initiated_at < '2026-07-01'
            GROUP BY m.merchant_id, m.merchant_name
            ORDER BY gmv DESC
            LIMIT 10;
        """,
    },
    'daily_success_rate': {
        'name': 'Daily success rate (June 2026)',
        'sql': """
            SELECT initiated_at::date AS day, count(*) AS payments,
                   round(100.0 * count(*) FILTER (WHERE status = 'SUCCESS') / count(*), 2) AS success_pct
            FROM transactions
            WHERE initiated_at >= '2026-06-01' AND initiated_at < '2026-07-01'
            GROUP BY 1
            ORDER BY 1;
        """,
    },
}


def run_benchmark_query(conn, query_sql, num_runs=NUM_RUNS):
    """Run a benchmark query multiple times and return timing stats."""
    cur = conn.cursor()
    cur.execute("SET search_path TO gpay;")
    
    times = []
    rows_processed = 0
    
    for run in range(num_runs):
        # Use EXPLAIN ANALYZE to get execution time
        explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query_sql}"
        try:
            cur.execute(explain_sql)
            result = cur.fetchone()[0]
            exec_time = result[0].get('Execution Time', 0)
            planning_time = result[0].get('Planning Time', 0)
            times.append(exec_time)
            
            # Get actual rows from the plan
            plan = result[0].get('Plan', {})
            rows_processed = plan.get('Actual Rows', 0)
        except Exception as e:
            print(f"    Error: {e}")
            conn.rollback()
            times.append(-1)
    
    cur.close()
    
    valid_times = [t for t in times if t >= 0]
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        min_time = min(valid_times)
        max_time = max(valid_times)
    else:
        avg_time = min_time = max_time = -1
    
    return {
        'avg_ms': round(avg_time, 3),
        'min_ms': round(min_time, 3),
        'max_ms': round(max_time, 3),
        'rows_processed': rows_processed,
    }


def run_bulk_insert_benchmark(conn, data, num_runs=1):
    """Benchmark bulk transaction insertion."""
    cur = conn.cursor()
    cur.execute("SET search_path TO gpay;")
    
    # Prepare a subset of transactions for insert testing
    txns = data['transactions'][:1000]  # Insert 1000 txns for benchmarking
    
    times = []
    for run in range(num_runs):
        # Start a transaction we'll roll back
        cur.execute("BEGIN;")
        
        # Build COPY data
        buf = io.StringIO()
        writer = csv.writer(buf)
        for row in txns:
            # Modify txn_id and upi_ref to avoid conflicts
            modified_row = list(row)
            modified_row[0] = row[0] + 90000000 + run * 1000  # Offset txn_id
            modified_row[1] = f"{900000000000 + row[0] + run * 1000}"  # Offset upi_ref
            writer.writerow([v if v is not None else '' for v in modified_row])
        buf.seek(0)
        
        start = time.perf_counter()
        try:
            cur.copy_expert("COPY transactions FROM STDIN WITH (FORMAT csv, NULL '')", buf)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            print(f"    Bulk insert error: {e}")
            times.append(-1)
        
        cur.execute("ROLLBACK;")
    
    valid_times = [t for t in times if t >= 0]
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        rows_per_sec = int(1000 / (avg_time / 1000)) if avg_time > 0 else 0
    else:
        avg_time = -1
        rows_per_sec = 0
    
    cur.close()
    
    return {
        'avg_ms': round(avg_time, 3),
        'min_ms': round(min(valid_times), 3) if valid_times else -1,
        'max_ms': round(max(valid_times), 3) if valid_times else -1,
        'rows_processed': 1000,
        'throughput': rows_per_sec,
    }


# =====================================================================
# Main Benchmark Runner
# =====================================================================

def run_benchmarks():
    """Run the complete benchmark suite."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(DATASETS_DIR, exist_ok=True)
    
    results = []
    
    for dataset_size in DATASET_SIZES:
        print(f"\n{'='*70}")
        print(f"BENCHMARKING WITH {dataset_size:,} TRANSACTIONS")
        print(f"{'='*70}")
        
        # Generate synthetic data
        random.seed(RANDOM_SEED)  # Reset seed for reproducibility
        data = generate_synthetic_data(dataset_size)
        
        num_users = len(data['users'])
        
        # Benchmark on both configurations
        for config_name, db_name in [('non_partitioned', BASELINE_DB), ('partitioned', PARTITIONED_DB)]:
            print(f"\n--- Configuration: {config_name} ({db_name}) ---")
            
            try:
                conn = psycopg2.connect(database=db_name, **DB_CONFIG)
                conn.autocommit = True
            except Exception as e:
                print(f"  ERROR: Cannot connect to {db_name}: {e}")
                continue
            
            # Load data
            print(f"  Loading {dataset_size:,} transactions...")
            try:
                load_data_to_db(conn, data)
            except Exception as e:
                print(f"  ERROR loading data: {e}")
                conn.rollback()
                conn.close()
                continue
            
            is_partitioned = config_name == 'partitioned'
            
            # Run benchmark queries
            for query_key, query_info in BENCHMARK_QUERIES.items():
                print(f"  Benchmarking: {query_info['name']}...")
                result = run_benchmark_query(conn, query_info['sql'])
                
                throughput = 0
                if result['avg_ms'] > 0 and result['rows_processed'] > 0:
                    throughput = int(result['rows_processed'] / (result['avg_ms'] / 1000))
                
                results.append({
                    'dataset_size': dataset_size,
                    'users': num_users,
                    'configuration': config_name,
                    'partitioning': 'yes' if is_partitioned else 'no',
                    'operation': query_info['name'],
                    'execution_time_ms': result['avg_ms'],
                    'rows_processed': result['rows_processed'],
                    'throughput_rows_per_second': throughput,
                    'measurement_status': 'measured' if result['avg_ms'] >= 0 else 'error',
                })
                print(f"    → {result['avg_ms']:.3f} ms, {result['rows_processed']} rows")
            
            # Bulk insert benchmark
            print(f"  Benchmarking: Bulk transaction insertion...")
            insert_result = run_bulk_insert_benchmark(conn, data)
            results.append({
                'dataset_size': dataset_size,
                'users': num_users,
                'configuration': config_name,
                'partitioning': 'yes' if is_partitioned else 'no',
                'operation': 'Bulk transaction insertion (1000 rows)',
                'execution_time_ms': insert_result['avg_ms'],
                'rows_processed': insert_result['rows_processed'],
                'throughput_rows_per_second': insert_result.get('throughput', 0),
                'measurement_status': 'measured' if insert_result['avg_ms'] >= 0 else 'error',
            })
            print(f"    → {insert_result['avg_ms']:.3f} ms, {insert_result.get('throughput', 0)} rows/sec")
            
            conn.close()
    
    # Write results to CSV
    summary_path = os.path.join(RESULTS_DIR, 'summary.csv')
    fieldnames = [
        'dataset_size', 'users', 'configuration', 'partitioning',
        'operation', 'execution_time_ms', 'rows_processed',
        'throughput_rows_per_second', 'measurement_status'
    ]
    
    with open(summary_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n{'='*70}")
    print(f"Results written to: {summary_path}")
    print(f"Total benchmarks: {len(results)}")
    print(f"{'='*70}")
    
    return results


if __name__ == '__main__':
    run_benchmarks()

