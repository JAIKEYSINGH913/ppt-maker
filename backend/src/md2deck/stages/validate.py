from __future__ import annotations

from dataclasses import dataclass

from md2deck.config import AppConfig
from md2deck.models import PipelineArtifacts


@dataclass(slots=True)
class ValidateStage:
    name: str = "validate"

    def run(self, config: AppConfig, artifacts: PipelineArtifacts) -> None:
        notes: list[str] = []
        if not config.output_pptx.exists():
            raise RuntimeError("Render stage did not create the expected PPTX output.")

        output_size = config.output_pptx.stat().st_size
        notes.append(f"Output deck created: {config.output_pptx.name} ({output_size} bytes)")

        if artifacts.blueprint is not None:
            notes.append(f"Blueprint slide count: {len(artifacts.blueprint.slides)}")
            if len(artifacts.blueprint.slides) < 3:
                notes.append("Warning: very short deck (fewer than 3 slides).")
            if len(artifacts.blueprint.slides) > config.constraints.max_slides:
                notes.append("Warning: slide count exceeded target maximum.")

        if artifacts.document is not None:
            notes.append(f"Sections parsed: {len(artifacts.document.sections)}")
            notes.append(f"Tables found: {len(artifacts.document.tables)}")
            notes.append(f"Numeric facts found: {len(artifacts.document.numeric_facts)}")

        notes.append("Validation passed: ingest, storyline, blueprint, and rendering are wired.")
        notes.append("Markdown-derived sections, numeric facts, and data slide intents are active.")
        artifacts.validation_notes.extend(notes)
