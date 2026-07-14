from __future__ import annotations

"""SQLite persistence for the standalone scenario-quality evaluator."""

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tests.manual.quality_eval.judge import JudgeResult
    from tests.manual.quality_eval.layer1_checks import CheckResult


class QualityStore:
    """Store evaluator output beside the existing pipeline-runner metrics."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> QualityStore:
        self.ensure_schema()
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def ensure_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS quality_evals (
                eval_id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                mi_event_id INTEGER NOT NULL,
                scenario_group_id INTEGER,
                judge_model TEXT,
                prompt_version TEXT,
                created_at REAL NOT NULL DEFAULT (unixepoch())
            );
            CREATE TABLE IF NOT EXISTS quality_check_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eval_id INTEGER NOT NULL,
                check_id TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT NOT NULL,
                offenders_json TEXT NOT NULL,
                FOREIGN KEY (eval_id) REFERENCES quality_evals(eval_id)
            );
            CREATE TABLE IF NOT EXISTS quality_judge_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eval_id INTEGER NOT NULL,
                judge_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                verdict TEXT NOT NULL,
                violations_json TEXT NOT NULL,
                FOREIGN KEY (eval_id) REFERENCES quality_evals(eval_id)
            );
            CREATE TABLE IF NOT EXISTS validation_probe_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eval_id INTEGER,
                mutation_id TEXT NOT NULL,
                expected TEXT NOT NULL,
                observed TEXT NOT NULL,
                verdict TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at REAL NOT NULL DEFAULT (unixepoch()),
                FOREIGN KEY (eval_id) REFERENCES quality_evals(eval_id)
            );
            CREATE TABLE IF NOT EXISTS golden_case_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eval_id INTEGER,
                golden_id TEXT NOT NULL,
                matched TEXT NOT NULL,
                missed TEXT NOT NULL,
                extra TEXT NOT NULL,
                judge_ids TEXT NOT NULL,
                detail TEXT NOT NULL,
                created_at REAL NOT NULL DEFAULT (unixepoch()),
                FOREIGN KEY (eval_id) REFERENCES quality_evals(eval_id)
            );
            """,
        )
        self.conn.commit()

    def record_eval(
        self,
        *,
        batch_id: str,
        mi_event_id: int,
        scenario_group_id: int | None,
        judge_model: str | None,
        prompt_version: str | None,
    ) -> int:
        cursor = self.conn.execute(
            """
            INSERT INTO quality_evals
                (batch_id, mi_event_id, scenario_group_id, judge_model, prompt_version)
            VALUES (?, ?, ?, ?, ?)
            """,
            (batch_id, mi_event_id, scenario_group_id, judge_model, prompt_version),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def record_checks(self, eval_id: int, checks: Iterable[CheckResult]) -> None:
        rows = [
            (eval_id, check.check_id, check.status, check.detail, _json(list(check.offenders)))
            for check in checks
        ]
        self.conn.executemany(
            """
            INSERT INTO quality_check_results (eval_id, check_id, status, detail, offenders_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def update_eval_metadata(self, eval_id: int, *, judge_model: str, prompt_version: str) -> None:
        """Fill connector-resolved model metadata after bounded judge execution."""
        self.conn.execute(
            "UPDATE quality_evals SET judge_model = ?, prompt_version = ? WHERE eval_id = ?",
            (judge_model, prompt_version, eval_id),
        )
        self.conn.commit()

    def record_judge(self, eval_id: int, result: JudgeResult) -> None:
        rows = [
            (
                eval_id,
                item.judge_id,
                item.score,
                item.verdict,
                _json([violation.model_dump() for violation in item.violations]),
            )
            for item in result.items
        ]
        self.conn.executemany(
            """
            INSERT INTO quality_judge_scores (eval_id, judge_id, score, verdict, violations_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def record_probe(
        self,
        *,
        eval_id: int | None,
        mutation_id: str,
        expected: str,
        observed: str,
        verdict: str,
        detail: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO validation_probe_results
                (eval_id, mutation_id, expected, observed, verdict, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (eval_id, mutation_id, expected, observed, verdict, detail),
        )
        self.conn.commit()

    def record_golden(
        self,
        *,
        eval_id: int | None,
        golden_id: str,
        matched: Any,
        missed: Any,
        extra: Any,
        judge_ids: Any,
        detail: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO golden_case_results
                (eval_id, golden_id, matched, missed, extra, judge_ids, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (eval_id, golden_id, _json(matched), _json(missed), _json(extra), _json(judge_ids), detail),
        )
        self.conn.commit()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)
