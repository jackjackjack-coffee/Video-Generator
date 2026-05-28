from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class GenRequest(BaseModel):
    prompt: str
    references: list[Path] = Field(default_factory=list)
    aspect_ratio: str = "9:16"
    seed: int | None = None
    model: str | None = None
    extra: dict = Field(default_factory=dict)


class GenResult(BaseModel):
    path: Path
    variant_paths: list[Path] = Field(default_factory=list)
    source_url: str | None = None
    model_used: str
    raw_meta: dict = Field(default_factory=dict)


@runtime_checkable
class ImageAdapter(Protocol):
    name: str

    async def generate(self, req: GenRequest, out_dir: Path) -> GenResult: ...


@runtime_checkable
class VideoAdapter(Protocol):
    name: str

    async def generate(self, req: GenRequest, out_dir: Path) -> GenResult: ...


@runtime_checkable
class VoiceAdapter(Protocol):
    name: str

    async def synthesize(
        self,
        text: str,
        voice: str,
        out_dir: Path,
        style: str | None = None,
        item_id: str | None = None,
    ) -> GenResult: ...


@runtime_checkable
class AudioSearchAdapter(Protocol):
    name: str

    async def search_and_pick(
        self,
        query: str,
        kind: Literal["music", "sfx"],
        duration_s: tuple[int, int] | None,
        out_dir: Path,
        top_k: int = 5,
    ) -> list[GenResult]: ...


@runtime_checkable
class ComposeAdapter(Protocol):
    name: str

    async def render(self, project_dir: Path, run_dir: Path, out: Path) -> Path: ...


_REGISTRY: dict[str, type] = {}


def register(name: str):
    """Decorator: register an adapter implementation by name (used in project.yaml)."""

    def deco(cls):
        _REGISTRY[name] = cls
        cls.name = name
        return cls

    return deco


def get_adapter(name: str) -> type:
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown adapter '{name}'. Registered: {sorted(_REGISTRY.keys())}"
        )
    return _REGISTRY[name]


def list_adapters() -> list[str]:
    return sorted(_REGISTRY.keys())
