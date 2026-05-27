"""SQLite-backed persistence for historical benchmark results."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from agentbench.models import ScoreReport


class BenchmarkStore:
    """SQLite store for persisting and querying historical benchmark runs."""

    def __init__(self, db_path: str | Path = "agentbench.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                agent_version TEXT DEFAULT '',
                overall_score REAL NOT NULL,
                total_tests INTEGER DEFAULT 0,
                passed_tests INTEGER DEFAULT 0,
                failed_tests INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0.0,
                categories TEXT DEFAULT '[]',
                config TEXT DEFAULT '{}',
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                test_id TEXT NOT NULL,
                test_name TEXT DEFAULT '',
                category TEXT DEFAULT '',
                status TEXT NOT NULL,
                score REAL DEFAULT 0.0,
                response_time_ms REAL DEFAULT 0.0,
                detected INTEGER DEFAULT 0,
                error_message TEXT DEFAULT '',
                FOREIGN KEY (run_id) REFERENCES benchmark_runs(id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_agent
            ON benchmark_runs(agent_id, timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_score
            ON benchmark_runs(overall_score)
        """)
        conn.commit()
        conn.close()

    def save(self, report: ScoreReport) -> int:
        """Save a benchmark report to the store.

        Args:
            report: Score report to persist.

        Returns:
            The row ID of the saved run.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            categories_json = json.dumps([c.model_dump() for c in report.categories])
            config_json = json.dumps(report.config, default=str)

            cursor = conn.execute(
                """INSERT INTO benchmark_runs
                   (agent_id, agent_version, overall_score, total_tests,
                    passed_tests, failed_tests, duration_seconds,
                    categories, config, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    report.agent_id,
                    report.agent_version,
                    report.overall_score,
                    report.total_tests,
                    report.passed_tests,
                    report.failed_tests,
                    report.duration_seconds,
                    categories_json,
                    config_json,
                    report.timestamp.isoformat() if hasattr(report.timestamp, "isoformat") else str(report.timestamp),
                ),
            )
            run_id = cursor.lastrowid or 0

            for r in report.results:
                conn.execute(
                    """INSERT INTO test_results
                       (run_id, test_id, test_name, category, status,
                        score, response_time_ms, detected, error_message)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        r.test_case.id,
                        r.test_case.name,
                        r.test_case.category,
                        r.status.value,
                        r.score,
                        r.response_time_ms,
                        1 if r.detected else 0,
                        r.error_message,
                    ),
                )

            conn.commit()
            return run_id
        finally:
            conn.close()

    def list_runs(
        self,
        agent_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List historical benchmark runs.

        Args:
            agent_id: Optional filter by agent ID.
            limit: Maximum number of runs to return.
            offset: Pagination offset.

        Returns:
            List of run summary dicts.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            if agent_id:
                rows = conn.execute(
                    """SELECT id, agent_id, agent_version, overall_score,
                              total_tests, passed_tests, failed_tests,
                              duration_seconds, timestamp
                       FROM benchmark_runs
                       WHERE agent_id = ?
                       ORDER BY timestamp DESC
                       LIMIT ? OFFSET ?""",
                    (agent_id, limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT id, agent_id, agent_version, overall_score,
                              total_tests, passed_tests, failed_tests,
                              duration_seconds, timestamp
                       FROM benchmark_runs
                       ORDER BY timestamp DESC
                       LIMIT ? OFFSET ?""",
                    (limit, offset),
                ).fetchall()

            return [
                {
                    "id": r[0],
                    "agent_id": r[1],
                    "agent_version": r[2],
                    "overall_score": r[3],
                    "total_tests": r[4],
                    "passed_tests": r[5],
                    "failed_tests": r[6],
                    "duration_seconds": r[7],
                    "timestamp": r[8],
                }
                for r in rows
            ]
        finally:
            conn.close()

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        """Get a single benchmark run by ID.

        Args:
            run_id: The run ID.

        Returns:
            Run dict with results, or None if not found.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            row = conn.execute("SELECT * FROM benchmark_runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                return None

            results = conn.execute("SELECT * FROM test_results WHERE run_id = ?", (run_id,)).fetchall()

            return {
                "id": row[0],
                "agent_id": row[1],
                "agent_version": row[2],
                "overall_score": row[3],
                "total_tests": row[4],
                "passed_tests": row[5],
                "failed_tests": row[6],
                "duration_seconds": row[7],
                "categories": json.loads(row[8]),
                "config": json.loads(row[9]),
                "timestamp": row[10],
                "results": [
                    {
                        "test_id": rr[2],
                        "test_name": rr[3],
                        "category": rr[4],
                        "status": rr[5],
                        "score": rr[6],
                        "response_time_ms": rr[7],
                        "detected": bool(rr[8]),
                        "error_message": rr[9],
                    }
                    for rr in results
                ],
            }
        finally:
            conn.close()

    def delete_old_runs(self, keep: int = 100) -> int:
        """Delete all but the most recent runs.

        Args:
            keep: Number of recent runs to keep.

        Returns:
            Number of deleted rows.
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                """DELETE FROM benchmark_runs
                   WHERE id NOT IN (
                       SELECT id FROM benchmark_runs
                       ORDER BY timestamp DESC
                       LIMIT ?
                   )""",
                (keep,),
            )
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        finally:
            conn.close()
