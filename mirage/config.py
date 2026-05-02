from __future__ import annotations

import re
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator


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
    operator: Literal[
        "exists",
        "eq",
        "neq",
        "lt",
        "lte",
        "gt",
        "gte",
        "in",
        "not_in",
        "regex_match",
        "not_regex_match",
        "contains",
        "not_contains",
        "starts_with",
        "not_starts_with",
        "ends_with",
        "length_lte",
        "length_gte",
        "host_in",
        "host_not_in",
    ]
    message: str
    value: Any = None
    method: str | None = None
    path: str | None = None

    @model_validator(mode="after")
    def validate_operator_value(self) -> PolicyConfig:
        if self.operator in {"lt", "lte", "gt", "gte"} and not _is_numeric_value(self.value):
            raise ValueError(f"operator '{self.operator}' requires a numeric value.")
        if self.operator in {"in", "not_in"} and not isinstance(self.value, (list, tuple, set)):
            raise ValueError(f"operator '{self.operator}' requires a list, tuple, or set value.")
        if self.operator in {"regex_match", "not_regex_match"}:
            if not isinstance(self.value, str):
                raise ValueError(
                    f"operator '{self.operator}' requires a value that compiles as a regex."
                )
            try:
                re.compile(self.value)
            except re.error as exc:
                raise ValueError(
                    f"operator '{self.operator}' requires a value that compiles as a regex."
                ) from exc
        if self.operator in {"starts_with", "not_starts_with", "ends_with"} and not isinstance(
            self.value, str
        ):
            raise ValueError(f"operator '{self.operator}' requires a string value.")
        if self.operator in {"length_lte", "length_gte"}:
            if not isinstance(self.value, int) or isinstance(self.value, bool) or self.value < 0:
                raise ValueError(
                    f"operator '{self.operator}' requires a non-negative integer value."
                )
        if self.operator in {"host_in", "host_not_in"}:
            if not isinstance(self.value, (list, tuple)) or not self.value:
                raise ValueError(
                    f"operator '{self.operator}' requires a non-empty list of strings."
                )
            if not all(isinstance(item, str) for item in self.value):
                raise ValueError(
                    f"operator '{self.operator}' requires a non-empty list of strings."
                )
        return self


class MirageConfig(BaseModel):
    mocks: list[MockRouteConfig] = Field(default_factory=list)
    policies: list[PolicyConfig] = Field(default_factory=list)


class MirageConfigError(ValueError):
    """Raised when Mirage config (mocks.yaml / policies.yaml) is invalid.

    Subclasses ValueError so MirageEngine's existing config-error handling path
    catches it without change, while preserving a human-readable message that
    names the file, entry, and field at fault.
    """


@dataclass(frozen=True)
class MirageConfigSummary:
    mocks_path: str
    policies_path: str
    mock_count: int
    policy_count: int

    def to_text(self) -> str:
        return "\n".join(
            [
                "Mirage config valid.",
                f"Mocks: {self.mock_count} from {self.mocks_path}",
                f"Policies: {self.policy_count} from {self.policies_path}",
            ]
        )


_MOCK_EXAMPLE = """mocks:
  - name: get_supplier
    method: GET
    path: /v1/suppliers/SUP-001
    response:
      status_code: 200
      json:
        supplier_id: SUP-001
        status: approved"""


_POLICY_EXAMPLE = """policies:
  - name: enforce_bid_limit
    method: POST
    path: /v1/submit_bid
    field: bid_amount
    operator: lte
    value: 10000
    message: Agents cannot submit bids above the approved threshold."""


def load_mirage_config(mocks_path: Path, policies_path: Path) -> MirageConfig:
    mocks_data = _load_mapping_file(mocks_path)
    policies_data = _load_mapping_file(policies_path)
    mocks = _build_entries(
        mocks_data.get("mocks", []),
        MockRouteConfig,
        file_path=mocks_path,
        section="mocks",
        example=_MOCK_EXAMPLE,
    )
    policies = _build_entries(
        policies_data.get("policies", []),
        PolicyConfig,
        file_path=policies_path,
        section="policies",
        example=_POLICY_EXAMPLE,
    )
    return MirageConfig(mocks=mocks, policies=policies)


def load_policies_only(policies_path: Path) -> MirageConfig:
    """Load only the policy section from a policies file.

    Used by the gateway, which never dispatches mocks. It forwards to a
    real upstream. Returns a `MirageConfig` with an empty `mocks` list and
    populated `policies`, which lets `PolicyEvaluator` consume it without
    knowing whether the surrounding runtime is the CI engine or the gateway.
    """

    policies_data = _load_mapping_file(policies_path)
    policies = _build_entries(
        policies_data.get("policies", []),
        PolicyConfig,
        file_path=policies_path,
        section="policies",
        example=_POLICY_EXAMPLE,
    )
    return MirageConfig(mocks=[], policies=policies)


def validate_mirage_config(mocks_path: Path, policies_path: Path) -> MirageConfigSummary:
    config = load_mirage_config(mocks_path, policies_path)
    return MirageConfigSummary(
        mocks_path=str(mocks_path),
        policies_path=str(policies_path),
        mock_count=len(config.mocks),
        policy_count=len(config.policies),
    )


def _build_entries(
    entries: Any,
    model_cls: type[BaseModel],
    *,
    file_path: Path,
    section: str,
    example: str,
) -> list[BaseModel]:
    if not isinstance(entries, list):
        raise MirageConfigError(
            f"Mirage config error in {file_path.name}: "
            f"top-level key '{section}' must be a list, got {type(entries).__name__}.\n"
            f"Example of a valid file:\n{example}"
        )

    built: list[BaseModel] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise MirageConfigError(
                f"Mirage config error in {file_path.name} {section}[{index}]: "
                f"expected a mapping, got {type(entry).__name__}.\n"
                f"Example of a valid entry:\n{example}"
            )
        try:
            built.append(model_cls.model_validate(entry))
        except ValidationError as exc:
            raise MirageConfigError(
                _format_validation_error(
                    exc.errors(),
                    file_path=file_path,
                    section=section,
                    index=index,
                    entry=entry,
                    example=example,
                )
            ) from exc
    return built


def _format_validation_error(
    errors: Iterable[dict[str, Any]],
    *,
    file_path: Path,
    section: str,
    index: int,
    entry: dict[str, Any],
    example: str,
) -> str:
    name = entry.get("name") if isinstance(entry, dict) else None
    header = f"Mirage config error in {file_path.name} {section}[{index}]"
    if name:
        header += f" (name={name!r})"

    lines = [header + ":"]
    for error in errors:
        loc_parts = [str(part) for part in error.get("loc", ()) if part != "__root__"]
        loc = ".".join(loc_parts) or "(entry root)"
        lines.append(f"  - field '{loc}': {error.get('msg', 'invalid value')}")
    lines.append("Example of a valid entry:")
    lines.append(example)
    return "\n".join(lines)


def _load_mapping_file(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}

    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        yaml = None

    if yaml is not None:
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise MirageConfigError(
                f"Mirage config error in {path.name}: invalid YAML.\n{exc}"
            ) from exc
    else:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MirageConfigError(
                f"Mirage config error in {path.name}: invalid JSON.\n{exc}"
            ) from exc

    if not isinstance(data, dict):
        raise MirageConfigError(f"{path} must contain a top-level mapping.")

    return data


def _is_numeric_value(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
