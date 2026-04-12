from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from md2deck.config import AppConfig
from md2deck.models import PipelineArtifacts
from md2deck.stages.blueprint import BlueprintStage
from md2deck.stages.canva_enrich import CanvaEnrichStage
from md2deck.stages.ingest import IngestStage
from md2deck.stages.render import RenderStage
from md2deck.stages.storyliner import StorylinerStage
from md2deck.stages.theme import ThemeStage
from md2deck.stages.validate import ValidateStage


class DeckPipeline:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.artifacts = PipelineArtifacts()
        self._stages = [
            IngestStage(),
            ThemeStage(),
            StorylinerStage(),
            BlueprintStage(),
            CanvaEnrichStage(),
            RenderStage(),
            ValidateStage(),
        ]

    def run(self, callback: callable | None = None) -> PipelineArtifacts:
        self.config.output_pptx.parent.mkdir(parents=True, exist_ok=True)

        for stage in self._stages:
            if callback:
                callback(stage.name, "started")
            
            stage.run(self.config, self.artifacts)
            
            if callback:
                callback(stage.name, "completed")

        self._write_manifest()
        return self.artifacts

    def _write_manifest(self) -> None:
        manifest_path = self.config.output_pptx.with_suffix(".manifest.json")
        payload = {
            "input_markdown": str(self.config.input_markdown),
            "master_pptx": str(self.config.master_pptx),
            "output_pptx": str(self.config.output_pptx),
            "constraints": asdict(self.config.constraints),
            "visuals": asdict(self.config.visuals),
            "artifacts": {
                "document_title": self.artifacts.document.title if self.artifacts.document else None,
                "storyline_slide_target": (
                    self.artifacts.storyline.slide_target if self.artifacts.storyline else None
                ),
                "blueprint_slide_count": (
                    len(self.artifacts.blueprint.slides) if self.artifacts.blueprint else 0
                ),
                "section_count": len(self.artifacts.document.sections) if self.artifacts.document else 0,
                "table_count": len(self.artifacts.document.tables) if self.artifacts.document else 0,
                "numeric_fact_count": len(self.artifacts.document.numeric_facts) if self.artifacts.document else 0,
                "theme_layouts": self.artifacts.theme.layout_names if self.artifacts.theme else [],
                "validation_notes": self.artifacts.validation_notes,
            },
        }
        manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
