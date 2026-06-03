-- InsightFlow ETL notification triggers
-- ──────────────────────────────────────────────────────────────────────────────
-- Run against the OLTP source database (insightflow_app) via trigger_setup.py.
-- Any INSERT into a transaction table fires pg_notify('etl_trigger', <table>),
-- which the etl-listener service picks up to schedule an incremental ETL run.
--
-- Design notes
-- ─────────────
-- * FOR EACH STATEMENT (not FOR EACH ROW): one notification per batch, not per
--   row. A bulk upload of 10,000 rows sends exactly one notification.
-- * The listener debounces: the ETL only starts after a quiet period, so rapid
--   successive uploads are coalesced into a single pipeline run.
-- * All statements use CREATE OR REPLACE / DROP IF EXISTS — safe to re-run.
-- ──────────────────────────────────────────────────────────────────────────────

-- Shared trigger function: fires pg_notify with the table name as payload
CREATE OR REPLACE FUNCTION notify_etl_trigger()
RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify('etl_trigger', TG_TABLE_NAME);
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- ── POS ───────────────────────────────────────────────────────────────────────
-- Fires when a POS transaction line is inserted (the line is the unit of work)
DROP TRIGGER IF EXISTS trg_etl_pos ON "posTransactionLine";
CREATE TRIGGER trg_etl_pos
    AFTER INSERT ON "posTransactionLine"
    FOR EACH STATEMENT
    EXECUTE FUNCTION notify_etl_trigger();

-- ── Online orders ─────────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_etl_online ON "onlineOrderLine";
CREATE TRIGGER trg_etl_online
    AFTER INSERT ON "onlineOrderLine"
    FOR EACH STATEMENT
    EXECUTE FUNCTION notify_etl_trigger();

-- ── Feedback surveys ──────────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_etl_feedback ON "feedbackSurvey";
CREATE TRIGGER trg_etl_feedback
    AFTER INSERT ON "feedbackSurvey"
    FOR EACH STATEMENT
    EXECUTE FUNCTION notify_etl_trigger();

-- ── Inventory ─────────────────────────────────────────────────────────────────
-- Fires on INSERT and UPDATE: stock adjustments also need a warehouse refresh
DROP TRIGGER IF EXISTS trg_etl_inventory ON "inventory";
CREATE TRIGGER trg_etl_inventory
    AFTER INSERT OR UPDATE ON "inventory"
    FOR EACH STATEMENT
    EXECUTE FUNCTION notify_etl_trigger();
