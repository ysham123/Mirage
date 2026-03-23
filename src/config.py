from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class MockResponseConfig(BaseModel):
    status_code: int = 200
    body: Any = Field(default_factory=dict, alias="json")

    model_config = {"populate_by_name": True}


class MockRouteConfig(BaseModel):
    name: str
    method: str
    path: str
    response: MockResponseConfig


class PolicyConfig(BaseModel):
    name: str
    field: str
    operator: Literal["exists", "eq", "neq", "lt", "lte", "gt", "gte", "in", "not_in"]
    message: str
    value: Any = None
    method: str | None = None
    path: str | None = None


class MirageConfig(BaseModel):
    mocks: list[MockRouteConfig] = Field(default_factory=list)
    policies: list[PolicyConfig] = Field(default_factory=list)


def load_mirage_config(mocks_path: Path, policies_path: Path) -> MirageConfig:
    mocks_data = _load_mapping_file(mocks_path)
    policies_data = _load_mapping_file(policies_path)
    return MirageConfig(
        mocks=mocks_data.get("mocks", []),
        policies=policies_data.get("policies", []),
    )


def _load_mapping_file(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}

    try:
        import yaml  # type: ignore

        data = yaml.safe_load(raw)
    except ModuleNotFoundError:
        data = json.loads(raw)

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a top-level mapping.")

    return data
