from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, Field

from creativeforge.config import ProjectConfig


class StageContext(BaseModel):
    project_dir: Path
    run_dir: Path
    prev_outputs: dict[str, Path] = Field(default_factory=dict)
    config: ProjectConfig

    model_config = {"arbitrary_types_allowed": True}


class StageArtifact(BaseModel):
    id: str
    path: Path
    kind: str
    meta: dict = Field(default_factory=dict)


class StageResult(BaseModel):
    stage_id: str
    artifacts: list[StageArtifact] = Field(default_factory=list)
    notes: str = ""


class Stage(ABC):
    id: str = "stage"
    label: str = "Stage"

    @abstractmethod
    def items(self, ctx: StageContext) -> Iterable[str]: ...

    @abstractmethod
    async def generate_one(self, item_id: str, ctx: StageContext) -> StageArtifact: ...
