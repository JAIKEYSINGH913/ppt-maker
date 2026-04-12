
import sys
from pathlib import Path
import json

# Add src to path
src_root = Path(__file__).resolve().parent / "backend" / "src"
sys.path.append(str(src_root))

from md2deck.config import AppConfig, DeckConstraints
from md2deck.models import PipelineArtifacts
from md2deck.stages.ingest import IngestStage
from md2deck.stages.storyliner import StorylinerStage

def test_pipeline():
    md_content = """# Deep Dive Test
## Executive Summary
This is a long report.
* Point A
* Point B
* Point C
* Point D
"""
    # Add 25 sections to simulate subagent test
    for i in range(1, 26):
        md_content += f"\n## Section {i}\nThis is content for section {i}.\n"
        md_content += "\n".join([f"* Info {i}.{j} about specific topic" for j in range(1, 10)])
    
    test_md = Path("reproduction.md")
    test_md.write_text(md_content)
    
    config = AppConfig(
        input_markdown=test_md,
        master_pptx=Path("dummy.pptx"),
        output_pptx=Path("output.pptx"),
        working_dir=Path("."),
        constraints=DeckConstraints(min_slides=12, max_slides=20)
    )
    
    artifacts = PipelineArtifacts()
    
    # Run Ingest
    ingest = IngestStage()
    ingest.run(config, artifacts)
    print(f"Sections found: {len(artifacts.document.sections)}")
    
    # Run Storyliner
    storyliner = StorylinerStage()
    storyliner.run(config, artifacts)
    
    print(f"Slides generated: {len(artifacts.storyline.slides)}")
    for i, slide in enumerate(artifacts.storyline.slides):
        print(f"  {i+1}. {slide.title} ({slide.visual_intent})")

if __name__ == "__main__":
    test_pipeline()
