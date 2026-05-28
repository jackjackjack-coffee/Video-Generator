from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from ruamel.yaml import YAML

yaml = YAML(typ="safe")


class OutputSpec(BaseModel):
    width: int = 1080
    height: int = 1920
    fps: int = 30
    duration_s: int = 30


class ProjectMeta(BaseModel):
    id: str
    title: str
    description: str = ""
    output: OutputSpec = OutputSpec()


class StageSpec(BaseModel):
    adapter: str
    model: str | None = None
    aspect_ratio: str | None = None
    voice: str | None = None
    fallback_adapter: str | None = None
    prompts_file: str | None = None
    keywords_file: str | None = None
    items: list[str] | None = None
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
    composition_id: str | None = None
    project_remotion_dir: str | None = None
    output_filename: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class ApprovalConfig(BaseModel):
    mode: str = "gate"
    preview: str = "open"
    remember_choices: bool = False


class BrowserConfig(BaseModel):
    headed: bool = True
    storage_state: str | None = None
    user_data_dir: str | None = None


class VisualStyleEntry(BaseModel):
    palette: str = ""
    suffix: str = ""


class CreditsConfig(BaseModel):
    monthly_budget: int = 1000
    # Optional per-model cost override; falls back to credits.DEFAULT_VIDEO_COSTS.
    costs: dict[str, Any] = Field(default_factory=dict)


class ProjectConfig(BaseModel):
    project: ProjectMeta
    stages: dict[str, StageSpec]
    approval: ApprovalConfig = ApprovalConfig()
    browser: BrowserConfig = BrowserConfig()
    storyboard_file: str = "storyboard.yaml"
    visual_style: dict[str, VisualStyleEntry] = Field(default_factory=dict)
    credits: CreditsConfig = CreditsConfig()

    @classmethod
    def load(cls, project_dir: Path) -> "ProjectConfig":
        path = project_dir / "project.yaml"
        with path.open() as f:
            data = yaml.load(f)
        return cls.model_validate(data)
