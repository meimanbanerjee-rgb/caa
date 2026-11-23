# backend/app/storage/sqlite_store.py
# SQLite implementation of the BaseStorage interface.

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from backend.app.config import settings
from backend.app.storage.base import BaseStorage
from backend.app.models.dataset import DatasetModel
from backend.app.models.insight import AnalysisModel, InsightModel
from backend.app.models.chat import ChatMessage


class SqliteStore(BaseStorage):
    """SQLite-backed metadata and history persistence."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            self.db_path = settings.storage_dir / "insightforge.db"
        else:
            self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS datasets (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    analysis_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
                )
                """
            )
            conn.commit()

    def save_dataset(self, dataset: DatasetModel) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO datasets (id, filename, file_type, size_bytes, status, created_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset.id,
                    dataset.filename,
                    dataset.file_type,
                    dataset.size_bytes,
                    dataset.status,
                    dataset.created_at.isoformat(),
                    dataset.model_dump_json(),
                ),
            )
            conn.commit()

    def get_dataset(self, dataset_id: str) -> Optional[DatasetModel]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload FROM datasets WHERE id = ?", (dataset_id,))
            row = cursor.fetchone()
            if row:
                return DatasetModel.model_validate_json(row["payload"])
            return None

    def list_datasets(self) -> List[DatasetModel]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload FROM datasets ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [DatasetModel.model_validate_json(r["payload"]) for r in rows]

    def delete_dataset(self, dataset_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def save_analysis(self, analysis: AnalysisModel) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO analyses (id, domain, created_at, payload)
                VALUES (?, ?, ?, ?)
                """,
                (
                    analysis.id,
                    analysis.domain,
                    analysis.created_at.isoformat(),
                    analysis.model_dump_json(),
                ),
            )
            conn.commit()

    def get_analysis(self, analysis_id: str) -> Optional[AnalysisModel]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload FROM analyses WHERE id = ?", (analysis_id,))
            row = cursor.fetchone()
            if row:
                return AnalysisModel.model_validate_json(row["payload"])
            return None

    def list_analyses(self) -> List[AnalysisModel]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload FROM analyses ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [AnalysisModel.model_validate_json(r["payload"]) for r in rows]

    def get_insight_evidence(self, analysis_id: str, insight_id: str) -> Optional[Dict[str, Any]]:
        analysis = self.get_analysis(analysis_id)
        if not analysis:
            return None
        for ins in analysis.insights:
            if ins.id == insight_id:
                return {
                    "insight_id": ins.id,
                    "title": ins.title,
                    "evidence": ins.evidence,
                    "method_or_formula": ins.method_or_formula,
                    "source": ins.source.model_dump(),
                    "reliability": ins.reliability.model_dump(),
                    "assumptions_and_limitations": ins.assumptions_and_limitations,
                }
        return None

    def save_chat_message(self, analysis_id: str, message: ChatMessage) -> None:
        import uuid
        msg_id = message.id or str(uuid.uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO chat_messages (id, analysis_id, role, created_at, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    msg_id,
                    analysis_id,
                    message.role,
                    message.timestamp.isoformat(),
                    message.model_dump_json(),
                ),
            )
            conn.commit()

    def get_chat_history(self, analysis_id: str) -> List[ChatMessage]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT payload FROM chat_messages WHERE analysis_id = ? ORDER BY created_at ASC",
                (analysis_id,),
            )
            rows = cursor.fetchall()
            return [ChatMessage.model_validate_json(r["payload"]) for r in rows]


store = SqliteStore()
