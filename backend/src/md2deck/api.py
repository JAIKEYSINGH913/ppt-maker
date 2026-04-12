from __future__ import annotations

import os
import sys
import json
import uuid
import asyncio
import pickle
import zipfile
from pathlib import Path
from typing import Dict, Any, List

# Add the 'src' directory to sys.path to resolve the 'md2deck' package correctly
src_root = str(Path(__file__).resolve().parent.parent)
if src_root not in sys.path:
    sys.path.insert(0, src_root)

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import aiofiles

from md2deck.config import AppConfig
from md2deck.pipeline import DeckPipeline

app = FastAPI(title="Spectral Weaver API", version="2.0.0")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
async def ping():
    return {"status": "online", "version": "2.0.0"}

# In-memory job store
JOBS: Dict[str, Dict[str, Any]] = {}
# Store pipeline artifacts for preview
ARTIFACTS: Dict[str, List[dict]] = {}
# Store the actual objects for re-rendering
PIPELINE_DATA: Dict[str, Any] = {}

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "exports"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MASTER_DIR = BASE_DIR.parent / "Slide Master"
TEMPLATES_META = BASE_DIR / "src/md2deck/templates_meta.json"
THUMBNAILS_DIR = BASE_DIR / "thumbnails"
THUMBNAILS_DIR.mkdir(exist_ok=True)

# Mount thumbnails as static files so the frontend can <img src="..."> them
app.mount("/thumbnails", StaticFiles(directory=str(THUMBNAILS_DIR)), name="thumbnails")


class PipelineTracker:
    def __init__(self, job_id: str):
        self.job_id = job_id

    def __call__(self, stage_name: str, status: str):
        if self.job_id in JOBS:
            JOBS[self.job_id]["stages"][stage_name] = status
            if status == "started":
                JOBS[self.job_id]["current_stage"] = stage_name


@app.post("/process")
async def process_markdown(
    background_tasks: BackgroundTasks,
    markdown_file: UploadFile = File(...),
    master_file: UploadFile | None = File(None),
    template_id: str | None = Form(None)
):
    job_id = str(uuid.uuid4())
    
    md_path = UPLOAD_DIR / f"{job_id}_{markdown_file.filename}"
    master_path = None
    
    if master_file:
        master_path = UPLOAD_DIR / f"{job_id}_{master_file.filename}"
        async with aiofiles.open(master_path, 'wb') as f:
            content = await master_file.read()
            await f.write(content)
    elif template_id:
        # Resolve from slide master folder using fuzzy matching
        tid_low = str(template_id).lower()
        print(f"Resolving template for ID: {tid_low}")
        
        # Priority 1: Exact id match
        for file in MASTER_DIR.glob("*.pptx"):
            if file.stem.lower() == tid_low:
                master_path = file
                break
        
        # Priority 2: Substring match
        if not master_path:
            for file in MASTER_DIR.glob("*.pptx"):
                fname = file.stem.lower()
                if tid_low in fname or fname in tid_low:
                    master_path = file
                    break
        
        if not master_path:
            # Fallback to the first available if anything is found
            all_masters = list(MASTER_DIR.glob("*.pptx"))
            if all_masters:
                master_path = all_masters[0]
                print(f"Fallback match to: {master_path}")
        
        if master_path:
            print(f"Matched Master Path: {master_path}")
        else:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    else:
        raise HTTPException(status_code=400, detail="Must provide either master_file or template_id")
    clean_name = Path(markdown_file.filename).stem
    output_filename = f"{clean_name}.pptx"
    output_path = OUTPUT_DIR / f"{clean_name}_{job_id}.pptx"

    # Save markdown
    async with aiofiles.open(md_path, 'wb') as f:
        content = await markdown_file.read()
        await f.write(content)

    JOBS[job_id] = {
        "id": job_id,
        "status": "processing",
        "current_stage": "initializing",
        "stages": {},
        "output_filename": output_filename,
        "disk_path": str(output_path),
        "md_path": str(md_path),
        "error": None,
        "slide_count": 0,
    }

    background_tasks.add_task(run_deck_pipeline, job_id, md_path, master_path, output_path)
    
    return {"job_id": job_id}


def run_deck_pipeline(job_id: str, md_path: Path, master_path: Path, output_path: Path):
    try:
        config = AppConfig(
            input_markdown=md_path,
            master_pptx=master_path,
            output_pptx=output_path,
            working_dir=BASE_DIR
        )
        pipeline = DeckPipeline(config)
        tracker = PipelineTracker(job_id)
        
        artifacts = pipeline.run(callback=tracker)
        
        # Store preview data for the preview endpoint
        template_id = master_path.stem
        ARTIFACTS[job_id] = artifacts.get_slide_previews(template_id=template_id)
        PIPELINE_DATA[job_id] = artifacts
        
        # PERSIST TO DISK to survive restarts
        artifacts_path = OUTPUT_DIR / f"{job_id}.artifacts"
        with open(artifacts_path, "wb") as f:
            pickle.dump(artifacts, f)
            
        JOBS[job_id]["slide_count"] = len(ARTIFACTS[job_id])
        JOBS[job_id]["status"] = "completed"
    except Exception as e:
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)
        print(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return JOBS[job_id]


@app.get("/preview/{job_id}")
async def get_preview(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_id in ARTIFACTS:
        return JSONResponse(content={
            "slides": ARTIFACTS[job_id],
            "total": len(ARTIFACTS[job_id]),
        })
    
    job = JOBS[job_id]
    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=job.get("error", "Pipeline failed"))
    
    return JSONResponse(content={
        "slides": [],
        "total": 0,
        "message": "Preview not yet available.",
    })


@app.post("/sync-layout/{job_id}")
async def sync_layout(job_id: str, payload: Dict[str, Any]):
    if job_id not in ARTIFACTS:
        raise HTTPException(status_code=404, detail="Job blueprint not found")
    
    slide_index = payload.get("index")
    overrides = payload.get("overrides")
    intent = payload.get("visual_intent")
    
    if slide_index is None:
        raise HTTPException(status_code=400, detail="Missing index")
    
    previews = ARTIFACTS[job_id]
    if 0 <= slide_index < len(previews):
        if overrides is not None:
            previews[slide_index]["overrides"] = overrides
        if intent is not None:
            previews[slide_index]["visual_intent"] = intent
        return {"status": "synced", "index": slide_index}
    
    raise HTTPException(status_code=404, detail="Slide index not found")


@app.post("/finalize/{job_id}")
async def finalize_job(job_id: str):
    """Re-render the PPTX using updated user overrides."""
    print(f"Finalizing job: {job_id}")
    if job_id not in PIPELINE_DATA:
        # Try to restore from disk
        artifacts_path = OUTPUT_DIR / f"{job_id}.artifacts"
        if artifacts_path.exists():
            print(f"Restoring artifacts from disk for job: {job_id}")
            with open(artifacts_path, "rb") as f:
                PIPELINE_DATA[job_id] = pickle.load(f)
        else:
            print(f"Job {job_id} not found in PIPELINE_DATA or disk. Keys available: {list(PIPELINE_DATA.keys())}")
            raise HTTPException(status_code=404, detail="Session expired. Please re-upload your markdown file to begin a new session.")
    
    try:
        artifacts = PIPELINE_DATA[job_id]
        previews = ARTIFACTS.get(job_id, [])
        
        # Sync ARTIFACTS overrides back to the live blueprint
        for i, slide in enumerate(artifacts.blueprint.slides):
            if i < len(previews):
                slide.user_overrides = previews[i].get("overrides", {})
                # Important: Allow user to manually change the visual intent from the UI
                if "visual_intent" in previews[i]:
                    slide.visual_intent = previews[i]["visual_intent"]

        job = JOBS[job_id]
        output_path = Path(job["disk_path"])
        
        # Re-run RenderStage
        from md2deck.stages.render import RenderStage
        from md2deck.stages.validate import ValidateStage
        
        # Ensure master path is absolute
        m_path = Path(artifacts.theme.master_path)
        if not m_path.is_absolute():
            m_path = MASTER_DIR / m_path.name
        
        if not m_path.exists():
             raise FileNotFoundError(f"Master PPTX not found at {m_path}")

        config = AppConfig(
            input_markdown=Path("dummy.md"), 
            master_pptx=m_path,
            output_pptx=output_path,
            working_dir=BASE_DIR
        )
        
        # Render with current overrides
        renderer = RenderStage()
        renderer.run(config, artifacts)
        
        # Re-validate
        validator = ValidateStage()
        validator.run(config, artifacts)
        
        return {"status": "finalized", "message": "PPTX re-rendered with your custom layout."}
    except Exception as e:
        print(f"Finalization failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{job_id}")
async def download_deck(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = JOBS[job_id]
    pptx_path = Path(job["disk_path"])
    md_path = Path(job["md_path"])
    manifest_path = pptx_path.with_suffix(".manifest.json")

    if not pptx_path.exists():
        raise HTTPException(status_code=404, detail="PPTX file not found on disk")
    
    # Create a ZIP package in the active output directory (Downloads)
    zip_filename = f"{pptx_path.stem}_Package.zip"
    zip_path = pptx_path.parent / zip_filename
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. Final Presentation
            zipf.write(pptx_path, arcname=job["output_filename"])
            # 2. Universal Slides JSON
            blueprint_path = BASE_DIR / "slide_blueprint.json"
            if blueprint_path.exists():
                zipf.write(blueprint_path, arcname="slides.json")
            # 3. Source Markdown
            if md_path.exists():
                zipf.write(md_path, arcname=md_path.name)
    except Exception as e:
        logger.error(f"Failed to create ZIP package: {e}")
        raise HTTPException(status_code=500, detail="Failed to package download")

    return FileResponse(
        zip_path, 
        filename=zip_filename,
        media_type="application/zip"
    )


@app.get("/templates")
async def get_templates():
    if not TEMPLATES_META.exists():
        return JSONResponse(content=[])
    
    async with aiofiles.open(TEMPLATES_META, mode='r') as f:
        content = await f.read()
        templates = json.loads(content)

    for tmpl in templates:
        tid = tmpl["id"]
        thumb_dir = THUMBNAILS_DIR / tid
        if thumb_dir.exists():
            slides = sorted(thumb_dir.glob("slide_*.png"))
            tmpl["slide_images"] = [
                f"/thumbnails/{tid}/{s.name}" for s in slides
            ]
        else:
            tmpl["slide_images"] = []

    return JSONResponse(content=templates)


@app.post("/templates/generate-thumbnails")
async def regenerate_thumbnails():
    from md2deck.thumbnailer import generate_thumbnails
    results = {}
    if not TEMPLATES_META.exists():
        return JSONResponse(content={"error": "No templates_meta.json found"})
    
    async with aiofiles.open(TEMPLATES_META, mode='r') as f:
        content = await f.read()
        templates = json.loads(content)

    for tmpl in templates:
        tid = tmpl["id"]
        pptx_path = MASTER_DIR / tmpl["filename"]
        if not pptx_path.exists():
            results[tid] = "PPTX not found"
            continue

        thumb_dir = THUMBNAILS_DIR / tid
        thumbs = generate_thumbnails(pptx_path, thumb_dir, force=True)
        results[tid] = f"{len(thumbs)} slides generated"

    return JSONResponse(content=results)


@app.get("/manifest/{job_id}")
async def get_manifest(job_id: str):
    if job_id not in JOBS or JOBS[job_id]["status"] != "completed":
        raise HTTPException(status_code=404, detail="Manifest not ready")
    
    manifest_path = OUTPUT_DIR / Path(JOBS[job_id]["output_filename"]).with_suffix(".manifest.json")
    if not manifest_path.exists():
         raise HTTPException(status_code=404, detail="Manifest not found")
         
    return FileResponse(manifest_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
