from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RunState:
    """File-backed run state. Survives process restarts so `resume` works."""

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.path = run_dir / "state.json"
        self._data: dict[str, Any] = {}

    @classmethod
    def create(cls, run_dir: Path, project_id: str, config_snapshot: dict) -> "RunState":
        run_dir.mkdir(parents=True, exist_ok=True)
        self = cls(run_dir)
        self._data = {
            "run_id": run_dir.name,
            "project": project_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "stages": {},
            "config_snapshot": config_snapshot,
            "model_versions": {},
            "credits_used": {"flow": 0, "gemini": 0},
        }
        self.save()
        return self

    @classmethod
    def load(cls, run_dir: Path) -> "RunState":
        self = cls(run_dir)
        with self.path.open(encoding="utf-8") as f:
            self._data = json.load(f)
        return self

    def save(self) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def stage(self, stage_id: str) -> dict:
        return self._data["stages"].setdefault(
            stage_id, {"status": "pending", "items": {}}
        )

    def set_stage_status(self, stage_id: str, status: str) -> None:
        st = self.stage(stage_id)
        st["status"] = status
        if status == "approved":
            st["approved_at"] = datetime.now(timezone.utc).isoformat()
        self.save()

    def record_item(self, stage_id: str, item_id: str, info: dict) -> None:
        st = self.stage(stage_id)
        st["items"][item_id] = info
        self.save()

    def record_model(self, adapter_name: str, model: str) -> None:
        self._data["model_versions"][adapter_name] = model
        self.save()

    def add_credits(self, source: str, amount: int) -> None:
        used = self._data.setdefault("credits_used", {"flow": 0, "gemini": 0})
        used[source] = used.get(source, 0) + amount
        self.save()

    def credits_used(self) -> dict[str, int]:
        return self._data.get("credits_used", {"flow": 0, "gemini": 0})

    @property
    def data(self) -> dict:
        return self._data
