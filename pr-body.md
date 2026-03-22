## Problem

Running multiple `sendalerts` or `sendreports` processes (e.g. one per container in an HA deployment) risks duplicate notifications or race conditions. Both commands were designed for single-instance operation.

## Solution

### sendalerts – `SELECT FOR UPDATE SKIP LOCKED`

On **PostgreSQL** and **MySQL 8.0+**, `sendalerts` now uses Django's
`select_for_update(skip_locked=True)` inside `transaction.atomic()` to distribute
`Flip` and `Check` processing across multiple concurrent workers:

- Each worker atomically claims a row; other workers skip already-locked rows instantly (`SKIP LOCKED`).
- If a worker crashes mid-transaction, the database releases its row locks automatically on connection close — no flip is permanently lost and no external cleanup is needed.
- No external coordination (Redis, Consul, ZooKeeper) is required.

On **SQLite** and other backends the original optimistic-lock pattern (`filter then conditional update`) is preserved unchanged, so single-instance deployments are unaffected.

### sendreports – distributed singleton lock

On **PostgreSQL**, `sendreports` acquires a session-level advisory lock
(`pg_try_advisory_lock`) on startup. On **MySQL 8.0+**, it uses `GET_LOCK()` with a
zero timeout. In both cases:

- Only one instance holds the lock and processes reports; additional instances log a message and exit immediately.
- If the primary instance crashes, the database releases the connection-scoped lock automatically, allowing a standby instance (restarted by a process supervisor or container restart policy) to become the new active worker.

On **SQLite** the lock step is skipped entirely.

### smtpd – no change needed

`smtpd` binds a network socket, so only one instance can listen on a given port by design. Place it behind a TCP load balancer or run it on a dedicated node; no code changes are required.

## Why this works

The `Flip` model already has a `processed` field and a partial index (`api_flip_not_processed`) for unprocessed rows. The `ping()` method already uses `select_for_update()`. This change extends the same pattern to the alert sender.

## Deployment model

```
Load Balancer
    │
    ├── Container 1:  gunicorn + manage.py sendalerts
    ├── Container 2:  gunicorn + manage.py sendalerts   ← safe, workers share Flips
    └── Container 3:  gunicorn + manage.py sendalerts

    ├── Container A:  manage.py sendreports --loop      ← holds lock, processes reports
    └── Container B:  manage.py sendreports --loop      ← exits; takes over if A stops

Shared PostgreSQL or MySQL (e.g. AWS RDS Multi-AZ)
```

## Limitations

- `SELECT FOR UPDATE SKIP LOCKED` requires **PostgreSQL** or **MySQL 8.0+** (MariaDB 10.6+). SQLite does not support it; the existing single-instance behaviour is preserved for SQLite deployments.
- The `sendreports` distributed lock requires the same database backends. SQLite deployments retain the original optimistic-lock behaviour.

## Testing

- New `test_sendalerts_ha.py`: covers the PostgreSQL/MySQL code path for `process_one_flip` and `handle_going_down`, plus the SQLite fallback.
- New `test_sendreports_ha.py`: covers advisory-lock acquisition, early exit when lock is held, clean release, and release-on-exception — for both PostgreSQL and MySQL.
- Existing test suites (`test_sendalerts.py`, `test_sendreports.py`) continue to pass unchanged.
