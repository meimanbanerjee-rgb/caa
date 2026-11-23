# backend/app/routes/datasets.py
# Endpoints for listing, inspecting, updating semantic field mappings, and deleting datasets.

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from backend.app.models.dataset import DatasetModel
from backend.app.storage.sqlite_store import store

router = APIRouter(tags=["Datasets"])


class FieldUpdatePayload(BaseModel):
    """Payload to confirm or reassign suggested column meanings."""
    column_name: str
    confirmed_meaning: str


@router.get("/datasets", response_model=List[DatasetModel])
def list_datasets() -> List[DatasetModel]:
    """Retrieve all uploaded datasets."""
    return store.list_datasets()


@router.get("/datasets/{dataset_id}", response_model=DatasetModel)
def get_dataset(dataset_id: str) -> DatasetModel:
    """Retrieve details, profiles, and data quality warnings for a specific dataset."""
    dataset = store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )
    return dataset


@router.patch("/datasets/{dataset_id}/fields", response_model=DatasetModel)
def update_field_meaning(dataset_id: str, payload: FieldUpdatePayload) -> DatasetModel:
    """User confirmation or modification of inferred column meanings."""
    dataset = store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )

    updated = False
    for table in dataset.tables:
        for col in table.columns:
            if col.name == payload.column_name:
                col.suggested_meaning = payload.confirmed_meaning
                col.meaning_status = "confirmed"
                updated = True

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Column '{payload.column_name}' not found in dataset.",
        )

    store.save_dataset(dataset)
    return dataset


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: str) -> Dict[str, Any]:
    """Deletes a dataset and cleans up its stored metadata."""
    success = store.delete_dataset(dataset_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found.",
        )
    return {"status": "deleted", "dataset_id": dataset_id}
