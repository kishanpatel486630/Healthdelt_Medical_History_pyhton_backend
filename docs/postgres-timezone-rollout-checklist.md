# Postgres Timezone Rollout Checklist (Expand/Contract, No Downtime)

This runbook covers safe rollout of timezone-aware datetimes in PostgreSQL for an already-running system.

Goal:
- Move timestamp columns from naive semantics to explicit UTC-aware semantics.
- Avoid user-facing downtime.
- Keep rollback options at each stage.

Assumptions:
- Application writes UTC values today.
- New app code already treats times as UTC-aware in Python.
- Current production DB is PostgreSQL (or planned to be).

## 0) Inventory and Decision

1. Enumerate impacted columns.
2. Classify each table by size and write throughput.
3. Choose strategy per table:
- Small table / low traffic: in-place type conversion.
- Large table / high traffic: shadow column + dual-write + backfill + swap.

Suggested target columns (based on model definitions):
- User.createdAt, User.updatedAt
- Doctor.createdAt, Doctor.updatedAt
- MedicalHistory.visitDate, MedicalHistory.createdAt, MedicalHistory.updatedAt
- Report.reportDate, Report.createdAt, Report.updatedAt
- Prescription.issuedDate, Prescription.expiryDate, Prescription.createdAt, Prescription.updatedAt
- Medicine.createdAt
- Appointment.date, Appointment.createdAt, Appointment.updatedAt
- Notification.createdAt
- OtpCode.expiresAt, OtpCode.createdAt
- RefreshToken.expiresAt, RefreshToken.createdAt
- EmergencyContact.createdAt
- AuditLog.createdAt
- MasterMedicine.createdAt
- MasterLabTest.createdAt
- MasterDisease.createdAt
- MasterTemplate.createdAt
- MasterCategory.createdAt

## 1) Preflight Safety Checks

1. Confirm backups and PITR are healthy.
2. Confirm replication lag alerting is active.
3. Confirm application metrics/dashboards are ready:
- Error rate
- Latency percentiles
- DB locks and long queries
4. Freeze unrelated schema changes for rollout window.

Data quality checks (run before migration):
```sql
-- Example: check for suspicious far-future/far-past values
SELECT COUNT(*) AS bad_rows
FROM "User"
WHERE "createdAt" < '2000-01-01'::timestamp
   OR "createdAt" > NOW() + INTERVAL '2 years';
```

## 2) Expand Phase (No Breaking Changes)

Use this for large or high-traffic tables.

1. Add shadow columns as timestamptz (nullable first).
2. Backfill in batches.
3. Add trigger/function for dual-write (old + new columns stay in sync).
4. Deploy app version that reads from new columns with fallback to old.

Example for one table/column pair:
```sql
-- 2.1 Add shadow column
ALTER TABLE "User" ADD COLUMN "createdAt_tz" timestamptz;

-- 2.2 Backfill existing rows, interpreting existing values as UTC
UPDATE "User"
SET "createdAt_tz" = "createdAt" AT TIME ZONE 'UTC'
WHERE "createdAt_tz" IS NULL;

-- 2.3 Keep columns in sync during rollout
CREATE OR REPLACE FUNCTION sync_user_createdat_tz() RETURNS trigger AS $$
BEGIN
  IF NEW."createdAt_tz" IS NULL AND NEW."createdAt" IS NOT NULL THEN
    NEW."createdAt_tz" := NEW."createdAt" AT TIME ZONE 'UTC';
  ELSIF NEW."createdAt" IS NULL AND NEW."createdAt_tz" IS NOT NULL THEN
    NEW."createdAt" := (NEW."createdAt_tz" AT TIME ZONE 'UTC');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_user_createdat_tz ON "User";
CREATE TRIGGER trg_sync_user_createdat_tz
BEFORE INSERT OR UPDATE ON "User"
FOR EACH ROW EXECUTE FUNCTION sync_user_createdat_tz();
```

Batch backfill pattern for very large tables:
```sql
-- Use primary key windows in application/ops script, e.g. 10k rows at a time
UPDATE "User"
SET "createdAt_tz" = "createdAt" AT TIME ZONE 'UTC'
WHERE id > :start_id AND id <= :end_id
  AND "createdAt_tz" IS NULL;
```

Validation checks:
```sql
SELECT COUNT(*) AS remaining_nulls
FROM "User"
WHERE "createdAt" IS NOT NULL AND "createdAt_tz" IS NULL;
```

## 3) Read Cutover

1. Deploy app release that reads timezone-aware shadow columns first.
2. Keep dual-write trigger active.
3. Run for at least one full traffic cycle.
4. Watch dashboards and logs.

## 4) Contract Phase

1. Enforce NOT NULL on shadow columns where required.
2. Drop old columns.
3. Rename shadow columns to original names.
4. Drop sync triggers/functions.

Example:
```sql
-- 4.1 Optional, only if original column was effectively non-null
ALTER TABLE "User" ALTER COLUMN "createdAt_tz" SET NOT NULL;

-- 4.2 Swap
ALTER TABLE "User" DROP COLUMN "createdAt";
ALTER TABLE "User" RENAME COLUMN "createdAt_tz" TO "createdAt";

-- 4.3 Cleanup trigger/function
DROP TRIGGER IF EXISTS trg_sync_user_createdat_tz ON "User";
DROP FUNCTION IF EXISTS sync_user_createdat_tz;
```

## 5) Alternative (In-Place Conversion for Small Tables)

For small/low-write tables only:
```sql
ALTER TABLE "SomeTable"
  ALTER COLUMN "someTimestamp" TYPE timestamptz
  USING "someTimestamp" AT TIME ZONE 'UTC';
```

This is simpler but can still lock/impact writes during DDL; use cautiously.

## 6) Rollback Plan by Phase

Expand phase rollback:
- Keep old columns as source of truth.
- Disable app read-from-shadow.
- Drop shadow columns/triggers if needed.

Read cutover rollback:
- Flip feature flag/config to read old columns.
- Keep dual-write active until stabilized.

Contract phase rollback:
- Hardest stage; do not start contract until confidence window passes.
- Take a fresh backup right before contract DDL.

## 7) Alembic Bootstrap (Repository Currently Missing Config)

Current repo state indicates `alembic` exists but appears uninitialized (no `alembic.ini`).

Bootstrap steps:
```bash
alembic init alembic
```

Then configure:
- `alembic.ini` -> `sqlalchemy.url`
- `alembic/env.py` -> set `target_metadata = Base.metadata`

Generate migration skeleton:
```bash
alembic revision -m "expand timezone columns" 
alembic revision -m "contract timezone columns"
```

Recommendation:
- Keep expand and contract in separate revisions.
- Do not rely blindly on autogenerate for timestamp semantics; hand-review SQL.

## 8) Operational Checklist

Before expand:
- [ ] Backup/PITR verified
- [ ] Feature flag for read source prepared
- [ ] Rollback owner assigned

During expand:
- [ ] Shadow columns added
- [ ] Batch backfill complete
- [ ] Sync triggers live
- [ ] Null-count validation = 0

Cutover:
- [ ] App reads shadow columns
- [ ] Error/latency stable for full traffic cycle

Contract:
- [ ] Fresh backup snapshot taken
- [ ] Old columns removed
- [ ] Shadow columns renamed
- [ ] Triggers/functions removed

After rollout:
- [ ] Post-migration consistency checks done
- [ ] Runbook/logs archived

## 9) Post-Migration Verification Queries

```sql
-- Ensure no naive leftovers in schema (Postgres)
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND data_type IN ('timestamp without time zone', 'timestamp with time zone')
ORDER BY table_name, column_name;
```

```sql
-- Spot-check recently written rows
SELECT "id", "createdAt"
FROM "User"
ORDER BY "createdAt" DESC
LIMIT 20;
```

---

Owner notes:
- Prefer UTC everywhere at storage and API boundaries.
- If clients send local times, normalize at API boundary and persist as UTC.
