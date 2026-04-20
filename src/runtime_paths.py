from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path


def resolve_config_path(
    *,
    explicit: str | Path | None,
    env_var: str,
    filename: str,
) -> Path:
    if explicit is not None:
        return Path(explicit)

    env_value = os.getenv(env_var)
    if env_value:
        return Path(env_value)

    working_copy_path = Path.cwd() / filename
    if working_copy_path.exists():
        return working_copy_path

    return Path(str(files("src").joinpath("defaults", filename)))


def resolve_artifact_root(explicit: str | Path | None = None) -> Path:
    if explicit is not None:
        return Path(explicit)

    env_value = os.getenv("MIRAGE_ARTIFACT_ROOT")
    if env_value:
        return Path(env_value)

    return Path.cwd() / "artifacts" / "traces"
