-- TimescaleDB: time-series hypertable support for efficient storage and querying
-- of time-stamped valuation data (prices, metrics, signals).
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- pgvector: vector similarity search for embedding-based lookups
-- (e.g. semantic search over financial documents or analyst notes).
CREATE EXTENSION IF NOT EXISTS vector;

-- pgcrypto: gen_random_uuid() default values used by ORM models.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS companies (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker varchar(20) UNIQUE NOT NULL,
    name varchar(100) NOT NULL,
    market varchar(10) NOT NULL,
    industry varchar(50) NOT NULL,
    competitors jsonb DEFAULT '[]'::jsonb,
    custom_groups jsonb DEFAULT '[]'::jsonb,
    is_active boolean DEFAULT true,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS financial_statements (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker varchar(20) NOT NULL,
    period date NOT NULL,
    market varchar(10) NOT NULL,
    revenue numeric(20, 2),
    net_profit numeric(20, 2),
    gross_margin double precision,
    roe double precision,
    contract_liabilities numeric(20, 2),
    total_assets numeric(20, 2),
    total_liabilities numeric(20, 2),
    operating_cashflow numeric(20, 2),
    eps numeric(10, 4),
    bvps numeric(10, 4),
    raw_data jsonb DEFAULT '{}'::jsonb,
    fetched_at timestamptz DEFAULT now(),
    CONSTRAINT uq_ticker_period UNIQUE (ticker, period)
);

CREATE TABLE IF NOT EXISTS industry_metrics (
    id bigserial,
    ticker varchar(20) NOT NULL,
    metric_name varchar(100) NOT NULL,
    metric_value double precision NOT NULL,
    recorded_at timestamptz NOT NULL,
    source varchar(50),
    confidence double precision DEFAULT 1.0,
    PRIMARY KEY (id, recorded_at)
);

SELECT create_hypertable('industry_metrics', 'recorded_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS ix_industry_metrics_ticker_metric_recorded
    ON industry_metrics (ticker, metric_name, recorded_at DESC);

CREATE TABLE IF NOT EXISTS master_signals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker varchar(20) NOT NULL,
    master_name varchar(30) NOT NULL,
    signal varchar(10) NOT NULL,
    confidence double precision,
    reasoning text,
    scoring_details jsonb DEFAULT '{}'::jsonb,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS debate_records (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker varchar(20) NOT NULL,
    rounds jsonb,
    judge_summary text,
    final_stance varchar(10),
    confidence double precision,
    key_contentions jsonb DEFAULT '[]'::jsonb,
    competitor_evidence_used jsonb DEFAULT '[]'::jsonb,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS valuation_reports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker varchar(20) NOT NULL,
    valuation_low numeric(20, 2),
    valuation_mid numeric(20, 2),
    valuation_high numeric(20, 2),
    pe_quantile double precision,
    bull_arguments jsonb DEFAULT '[]'::jsonb,
    bear_arguments jsonb DEFAULT '[]'::jsonb,
    key_assumptions jsonb DEFAULT '[]'::jsonb,
    sensitivity_factors jsonb DEFAULT '{}'::jsonb,
    competitor_comparison jsonb DEFAULT '{}'::jsonb,
    human_approved boolean DEFAULT false,
    approved_at timestamptz,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reflections (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id uuid REFERENCES valuation_reports(id),
    ticker varchar(20) NOT NULL,
    industry varchar(50),
    predicted_signal varchar(10),
    actual_outcome text,
    correct_arguments jsonb DEFAULT '[]'::jsonb,
    failed_arguments jsonb DEFAULT '[]'::jsonb,
    lesson_learned text,
    embedding vector(1024),
    created_at timestamptz DEFAULT now()
);
