# backend/app/storage/base.py
# Abstract storage interface for datasets, analyses, and history.

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from backend.app.models.dataset import DatasetModel
from backend.app.models.insight import AnalysisModel, InsightModel
from backend.app.models.chat import ChatMessage


class BaseStorage(ABC):
    """Abstract storage interface allowing drop-in database backends (SQLite, PostgreSQL)."""

    @abstractmethod
    def save_dataset(self, dataset: DatasetModel) -> None:
        pass

    @abstractmethod
    def get_dataset(self, dataset_id: str) -> Optional[DatasetModel]:
        pass

    @abstractmethod
    def list_datasets(self) -> List[DatasetModel]:
        pass

    @abstractmethod
    def delete_dataset(self, dataset_id: str) -> bool:
        pass

    @abstractmethod
    def save_analysis(self, analysis: AnalysisModel) -> None:
        pass

    @abstractmethod
    def get_analysis(self, analysis_id: str) -> Optional[AnalysisModel]:
        pass

    @abstractmethod
    def list_analyses(self) -> List[AnalysisModel]:
        pass

    @abstractmethod
    def get_insight_evidence(self, analysis_id: str, insight_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_chat_message(self, analysis_id: str, message: ChatMessage) -> None:
        pass

    @abstractmethod
    def get_chat_history(self, analysis_id: str) -> List[ChatMessage]:
        pass
