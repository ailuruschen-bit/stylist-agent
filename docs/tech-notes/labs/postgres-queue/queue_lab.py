"""Lab: build a job queue on PostgreSQL row locks and LISTEN/NOTIFY.

Each experiment uses separate connections, the same way separate worker
processes would. Timings are measured, not assumed.

Run:  DATABASE_URL=postgresql://lab@localhost:55432/postgres python queue_lab.py
Needs: psycopg 3 (pip install "psycopg[binary]")
"""

from __future__ import annotations

import os
import threading
import time

import psycopg

DSN = os.environ.get("DATABASE_URL", "postgresql://lab@localhost:55432/postgres")

FETCH_PLAIN = """
    SELECT id, task FROM jobs
    WHERE status = 'todo'
    ORDER BY id
    LIMIT 1
    FOR UPDATE
"""

FETCH_SKIP_LOCKED = """
    SELECT id, task FROM jobs
    WHERE status = 'todo'
    ORDER BY id
    LIMIT 1
    FOR UPDATE SKIP LOCKED
"""


def reset() -> None:
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS jobs")
        conn.execute(
            """
            CREATE TABLE jobs (
                id      bigserial PRIMARY KEY,
                task    text NOT NULL,
                status  text NOT NULL DEFAULT 'todo',
                worker  text
            )
            """
        )
        conn.execute(
            "INSERT INTO jobs (task) VALUES ('render_look_1'), ('render_look_2'), ('ingest_garment_3')"
        )


def show_jobs(title: str) -> None:
    with psycopg.connect(DSN, autocommit=True) as conn:
        rows = conn.execute("SELECT id, task, status, coalesce(worker, '-') FROM jobs ORDER BY id").fetchall()
    print(f"  {title}")
    for row in rows:
        print(f"    id={row[0]} task={row[1]:<17} status={row[2]:<6} worker={row[3]}")


def worker(name: str, fetch_sql: str, hold_seconds: float, start_at: float, log: list[str]) -> None:
    """Claim one job, pretend to work while holding the row lock, then mark it done."""
    time.sleep(max(0.0, start_at - time.monotonic()))
    with psycopg.connect(DSN) as conn:  # one transaction per claim
        t0 = time.monotonic()
        row = conn.execute(fetch_sql).fetchone()
        waited = time.monotonic() - t0
        if row is None:
            log.append(f"{name}: waited {waited:.2f}s, got no job")
            return
        log.append(f"{name}: waited {waited:.2f}s, got job {row[0]} ({row[1]})")
        conn.execute("UPDATE jobs SET status = 'doing', worker = %s WHERE id = %s", (name, row[0]))
        time.sleep(hold_seconds)
        conn.execute("UPDATE jobs SET status = 'done' WHERE id = %s", (row[0],))
    # Leaving the block commits and releases the row lock.


def run_two_workers(fetch_sql: str) -> None:
    log: list[str] = []
    start = time.monotonic() + 0.2
    a = threading.Thread(target=worker, args=("worker-A", fetch_sql, 2.0, start, log))
    b = threading.Thread(target=worker, args=("worker-B", fetch_sql, 0.0, start + 0.3, log))
    a.start(), b.start()
    a.join(), b.join()
    for line in log:
        print(f"  {line}")


def experiment_plain_for_update() -> None:
    print("\n[1] FOR UPDATE without SKIP LOCKED: B starts 0.3s after A")
    reset()
    run_two_workers(FETCH_PLAIN)
    show_jobs("jobs afterwards:")


def experiment_skip_locked() -> None:
    print("\n[2] FOR UPDATE SKIP LOCKED: B starts 0.3s after A")
    reset()
    run_two_workers(FETCH_SKIP_LOCKED)
    show_jobs("jobs afterwards:")


def experiment_crash_inside_transaction() -> None:
    print("\n[3] worker dies while its transaction is open")
    reset()
    conn = psycopg.connect(DSN)
    row = conn.execute(FETCH_SKIP_LOCKED).fetchone()
    conn.execute("UPDATE jobs SET status = 'doing', worker = 'worker-A' WHERE id = %s", (row[0],))
    print(f"  worker-A claimed job {row[0]} and set status=doing, transaction still open")
    with psycopg.connect(DSN, autocommit=True) as other:
        seen = other.execute("SELECT status FROM jobs WHERE id = %s", (row[0],)).fetchone()[0]
        print(f"  another connection sees job {row[0]} status={seen} (uncommitted change is invisible)")
    conn.close()  # connection drops without COMMIT, as if the process was killed
    print("  worker-A connection closed without COMMIT")
    show_jobs("jobs afterwards:")


def experiment_listen_notify() -> None:
    print("\n[4] LISTEN/NOTIFY: rollback, commit, and a listener that is not connected yet")
    reset()
    received: list[tuple[float, str]] = []
    t_start = time.monotonic()
    ready = threading.Event()

    def listener() -> None:
        with psycopg.connect(DSN, autocommit=True) as conn:
            conn.execute("LISTEN job_inserted")
            ready.set()
            for note in conn.notifies(timeout=3.0):
                received.append((time.monotonic() - t_start, note.payload))

    # A notification sent before anyone listens is simply lost.
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("SELECT pg_notify('job_inserted', 'sent-before-listen')")

    t = threading.Thread(target=listener)
    t.start()
    ready.wait()

    with psycopg.connect(DSN) as conn:
        conn.execute("INSERT INTO jobs (task) VALUES ('rolled_back_job')")
        conn.execute("SELECT pg_notify('job_inserted', 'from-rolled-back-tx')")
        conn.rollback()

    with psycopg.connect(DSN) as conn:
        conn.execute("INSERT INTO jobs (task) VALUES ('committed_job')")
        conn.execute("SELECT pg_notify('job_inserted', 'from-committed-tx')")
        sent_at = time.monotonic() - t_start
        time.sleep(1.0)  # keep the transaction open for a second before COMMIT
        commit_at = time.monotonic() - t_start
    # Leaving the block commits.

    t.join()
    print(f"  pg_notify called at {sent_at:.2f}s, COMMIT at about {commit_at:.2f}s")
    if not received:
        print("  listener received nothing")
    for at, payload in received:
        print(f"  listener received '{payload}' at {at:.2f}s")


CLAIM_ONE_STATEMENT = """
    WITH candidate AS (
        SELECT id FROM jobs
        WHERE status = 'todo'
        ORDER BY id
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    UPDATE jobs SET status = 'doing', worker = %s
    FROM candidate
    WHERE jobs.id = candidate.id
    RETURNING jobs.id, jobs.task
"""


def experiment_short_claim_and_stalled_job() -> None:
    print("\n[5] claim in one short transaction, then the worker dies")
    reset()
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS workers")
        conn.execute("CREATE TABLE workers (name text PRIMARY KEY, last_heartbeat timestamptz NOT NULL)")
        conn.execute("INSERT INTO workers VALUES ('worker-A', now())")
        row = conn.execute(CLAIM_ONE_STATEMENT, ("worker-A",)).fetchone()
        print(f"  worker-A claimed job {row[0]} ({row[1]}); the claim is already committed")
    print("  worker-A process dies: no more heartbeats, job never finishes")
    show_jobs("jobs right after the crash:")

    with psycopg.connect(DSN, autocommit=True) as conn:
        # Simulate 45 seconds passing without a heartbeat instead of sleeping.
        conn.execute("UPDATE workers SET last_heartbeat = now() - interval '45 seconds' WHERE name = 'worker-A'")
        stalled = conn.execute(
            """
            SELECT jobs.id, jobs.task, workers.name
            FROM jobs JOIN workers ON workers.name = jobs.worker
            WHERE jobs.status = 'doing'
              AND workers.last_heartbeat < now() - interval '30 seconds'
            """
        ).fetchall()
        print(f"  stalled jobs (worker heartbeat older than 30s): {stalled}")
        conn.execute(
            "UPDATE jobs SET status = 'todo', worker = NULL WHERE id = ANY(%s)",
            ([s[0] for s in stalled],),
        )
    show_jobs("jobs after retrying stalled jobs:")


def experiment_transactional_enqueue() -> None:
    print("\n[6] enqueue a job in the same transaction as business data")
    reset()
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS garments")
        conn.execute("CREATE TABLE garments (id bigserial PRIMARY KEY, name text NOT NULL)")
        conn.execute("DELETE FROM jobs")

    with psycopg.connect(DSN) as conn:
        gid = conn.execute("INSERT INTO garments (name) VALUES ('grey hoodie') RETURNING id").fetchone()[0]
        conn.execute("INSERT INTO jobs (task) VALUES (%s)", (f"ingest_garment_{gid}",))
        conn.rollback()  # e.g. the upload record failed validation later in the request
    with psycopg.connect(DSN) as conn:
        gid = conn.execute("INSERT INTO garments (name) VALUES ('navy shirt') RETURNING id").fetchone()[0]
        conn.execute("INSERT INTO jobs (task) VALUES (%s)", (f"ingest_garment_{gid}",))
    # Leaving the block commits both rows together.

    with psycopg.connect(DSN, autocommit=True) as conn:
        garments = conn.execute("SELECT id, name FROM garments ORDER BY id").fetchall()
        jobs = conn.execute("SELECT id, task, status FROM jobs ORDER BY id").fetchall()
    print(f"  garments: {garments}")
    print(f"  jobs:     {jobs}")


if __name__ == "__main__":
    experiment_plain_for_update()
    experiment_skip_locked()
    experiment_crash_inside_transaction()
    experiment_listen_notify()
    experiment_short_claim_and_stalled_job()
    experiment_transactional_enqueue()
