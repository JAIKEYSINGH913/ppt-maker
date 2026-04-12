"use client";

import { useState, useEffect } from "react";
import { DropZone } from "@/components/DropZone";
import { TelemetryStrip } from "@/components/TelemetryStrip";
import { WizardStepper } from "@/components/WizardStepper";
import { SlidePreview } from "@/components/SlidePreview";
import { TemplateSelector } from "@/components/TemplateSelector";
import { api, JobStatus, SlidePreviewData } from "@/lib/api";

export default function Home() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [slidePreviews, setSlidePreviews] = useState<SlidePreviewData[]>([]);
  const [wizardStep, setWizardStep] = useState(0);
  const [showPreview, setShowPreview] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // The selected template ID from the gallery
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  // The markdown file from the DropZone
  const [mdFile, setMdFile] = useState<File | null>(null);

  // Handle template selection from the gallery
  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplateId(templateId);
    // Proceed to processing immediately or let user click a button?
    // User said Stage 2 is template select, then processing. 
    // So we need a way to trigger process from stage 2.
    // I'll add a check in the next step.
  };

  const proceedToProcessing = async () => {
    if (!mdFile || !selectedTemplateId) return;
    try {
      setIsProcessing(true);
      setError(null);
      setWizardStep(2); // Move to Processing Stage
      const { job_id } = await api.process(mdFile, selectedTemplateId);
      setJobId(job_id);
    } catch (err) {
      console.error("api.process failed", err);
      setError("SERVER OFFLINE. CHECK PORT 8000.");
    } finally {
      setIsProcessing(false);
    }
  };

  useEffect(() => {
    if (!jobId) return;

    const interval = setInterval(async () => {
      try {
        const currentStatus = await api.getStatus(jobId);
        setStatus(currentStatus);

        if (currentStatus.status === "completed") {
          clearInterval(interval);
          try {
            const preview = await api.getPreview(jobId);
            if (preview.slides.length > 0) {
              setSlidePreviews(preview.slides);
              setWizardStep(3); // Move to Preview Stage
            } else {
              setWizardStep(4); // Move to Export Stage
            }
          } catch {
            setWizardStep(4);
          }
        }

        if (currentStatus.status === "failed") {
          clearInterval(interval);
          setError(currentStatus.error || "FATAL SYSTEM ERROR.");
        }
      } catch (err) {
        console.error("Telemetry failure:", err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [jobId]);

  const handlePreviewConfirm = () => {
    setWizardStep(4);
  };

  const reset = () => {
    setJobId(null);
    setStatus(null);
    setError(null);
    setSlidePreviews([]);
    setWizardStep(0);
    setShowPreview(false);
    setIsProcessing(false);
    setSelectedTemplateId(null);
    setMdFile(null);
  };

  return (
    <main className="min-h-screen flex flex-col items-center py-16 px-4 md:px-10">

      {/* Huge Retro Header */}
      <header className="w-full max-w-5xl flex flex-col items-center mb-16 text-center border-b-8 border-[#333] pb-10">
        <h1 className="text-5xl md:text-7xl lg:text-8xl font-pixel text-white mb-6 tracking-widest uppercase" style={{ textShadow: "6px 6px 0px var(--primary)" }}>
          SPECTRAL
        </h1>
        <p className="font-code text-2xl md:text-3xl text-[var(--accent)] tracking-widest uppercase">
          [ AGENTIC CANVAS ORCHESTRATOR ]
        </p>
      </header>

      {/* Main Orchestrator Stack */}
      <section className="w-full flex flex-col items-center gap-16 max-w-5xl flex-1">

        <WizardStepper currentStep={wizardStep} />

        {/* ─── Stage 1: Welcome & Data Ingest ────────── */}
        {wizardStep === 0 && !error && (
          <div className="w-full max-w-4xl flex flex-col gap-12 animate-in fade-in slide-in-from-bottom-8 duration-700">
            <div className="text-center space-y-6">
              <h2 className="font-pixel text-4xl md:text-5xl text-white uppercase tracking-tighter">
                Welcome to the <span className="text-[var(--primary)]">Spectral Engine</span>
              </h2>
              <p className="font-code text-xl text-white/60 tracking-widest max-w-2xl mx-auto uppercase">
                The most advanced AI pipeline for transforming markdown into high-fidelity executive presentations. 
                Upload your source data below to begin.
              </p>
            </div>

            <div
              onClick={() => document.getElementById("md-input")?.click()}
              className={`pixel-box p-16 cursor-pointer flex flex-col items-center gap-8 min-h-[300px] transition-all relative overflow-hidden group ${
                mdFile ? "pixel-box-primary border-[var(--primary)] shadow-[0_0_40px_rgba(57,255,20,0.2)]" : "pixel-box-hover border-white/10"
              }`}
            >
              <div className="absolute inset-0 bg-gradient-to-b from-[var(--primary)]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              
              <input
                id="md-input"
                type="file"
                className="hidden"
                accept=".md"
                onChange={(e) => {
                   const file = e.target.files?.[0] || null;
                   setMdFile(file);
                }}
              />
              
              <div className="z-10 text-center">
                <div className="w-20 h-20 border-4 border-dashed border-white/20 flex items-center justify-center mb-8 mx-auto group-hover:border-[var(--primary)] group-hover:rotate-45 transition-all">
                  <span className="text-4xl text-white/20 group-hover:text-[var(--primary)] group-hover:-rotate-45 transition-all">+</span>
                </div>
                <h2 className="font-pixel text-3xl md:text-4xl mb-6 text-white uppercase">
                  {mdFile ? mdFile.name : "INITIATE DATA LOAD"}
                </h2>
                <p className="font-code text-xl text-white/40 tracking-[0.2em] uppercase">
                  {mdFile ? `[ ${(mdFile.size / 1024).toFixed(1)} KB READY ]` : "Drop .MD file or click to browse filesystem"}
                </p>
              </div>
            </div>

            {mdFile && (
              <button
                onClick={() => setWizardStep(1)}
                className="btn-pixel w-full text-2xl py-8 shadow-[8px_8px_0_0_#FFF] hover:scale-105"
              >
                PROCEED TO MASTER SELECTION {">>"}
              </button>
            )}
          </div>
        )}

        {/* ─── Stage 2: Master Selection ────────────── */}
        {wizardStep === 1 && !error && (
          <div className="w-full max-w-5xl animate-in fade-in slide-in-from-right-8 duration-500">
             <div className="flex items-center gap-6 mb-8">
                <button
                  onClick={() => setWizardStep(0)}
                  className="btn-pixel !p-4 !text-xs bg-black/50 border-white/20 text-white/50 hover:text-white"
                >
                  {"<< BACK"}
                </button>
                <div className="h-px flex-1 bg-white/10" />
                <span className="font-pixel text-xs text-[var(--accent)] uppercase tracking-widest">
                  DATA: {mdFile?.name}
                </span>
             </div>
            <TemplateSelector onSelect={(id) => {
              setSelectedTemplateId(id);
              proceedToProcessing();
            }} isProcessing={isProcessing} />
          </div>
        )}

        {/* ─── Stage 3: Processing ────────────────────── */}
        {wizardStep === 2 && !error && (
          <div className="w-full flex flex-col items-center gap-12 animate-pulse py-20">
            <div className="text-center space-y-4">
              <h2 className="font-pixel text-4xl text-[var(--primary)] animate-bounce">
                [ PROCESSING CORE ]
              </h2>
              <p className="font-code text-white/40 uppercase tracking-[0.3em]">
                Orchestrating visual DNA and layout structures...
              </p>
            </div>
            <TelemetryStrip
              stages={status?.stages || {}}
              currentStage={status?.current_stage || ""}
            />
          </div>
        )}

        {/* ─── Stage 4: High-Fidelity Studio ───────────────── */}
        {wizardStep === 3 && slidePreviews.length > 0 && jobId && (
          <div className="w-full animate-in fade-in zoom-in-95 duration-500">
            <SlidePreview 
                jobId={jobId}
                initialSlides={slidePreviews} 
                onConfirm={handlePreviewConfirm} 
                onHome={reset}
            />
          </div>
        )}

        {/* ─── Stage 5: Export ──────────────────────── */}
        {wizardStep === 4 && status?.status === "completed" && !error && (
          <div className="pixel-box p-16 bg-[#0a0a0a] border-[var(--success)] shadow-[0_0_50px_rgba(0,255,255,0.2)] max-w-4xl w-full flex flex-col items-center gap-12 text-center animate-in zoom-in-90 duration-700">

            <div className="space-y-4">
              <span className="font-pixel text-6xl text-[var(--success)] block tracking-widest uppercase" style={{ textShadow: "0 0 20px var(--success)" }}>
                COMPILATION COMPLETE
              </span>
              <div className="flex items-center justify-center gap-4 text-white/40 font-code uppercase">
                <div className="h-px w-12 bg-white/20" />
                <span>Status: Mission Cleared</span>
                <div className="h-px w-12 bg-white/20" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full border-y-4 border-white/5 py-12">
               <div className="bg-black/40 p-6 border-l-4 border-[var(--primary)] text-left">
                  <label className="font-pixel text-[10px] text-white/30 block mb-2">OUTPUT LOG</label>
                  <p className="font-code text-2xl text-white uppercase">{status.slide_count} Slides Generated</p>
               </div>
               <div className="bg-black/40 p-6 border-l-4 border-[var(--accent)] text-left">
                  <label className="font-pixel text-[10px] text-white/30 block mb-2">FILE SYSTEM</label>
                  <p className="font-code text-lg text-white/60 truncate uppercase">{status.output_filename}</p>
               </div>
            </div>

            <div className="w-full flex flex-col md:flex-row gap-8">
              <a
                href={api.getDownloadUrl(jobId!)}
                download={status.output_filename}
                className="btn-pixel flex-1 flex items-center justify-center text-3xl py-10 bg-[var(--success)] text-black border-[var(--success)] hover:bg-white hover:border-white shadow-[10px_10px_0_0_#FFF]"
              >
                [ DOWNLOAD PACKAGE ]
              </a>

              <button
                onClick={reset}
                className="btn-pixel bg-black text-white/50 border-white/20 hover:text-[var(--accent)] hover:border-[var(--accent)] px-12"
              >
                NEW MISSION
              </button>
            </div>
            
            <button
               onClick={reset}
               className="font-pixel text-xs text-white/20 hover:text-white underline underline-offset-8 tracking-widest"
            >
               {"<< FULL REBOOT SYSTEM"}
            </button>
          </div>
        )}

        {/* ─── Error State ───────────────────────────── */}
        {error && (
          <div className="pixel-box p-12 !bg-red-900/20 !border-red-500 shadow-[0_0_40px_rgba(255,0,0,0.3)] w-full max-w-3xl text-center">
            <h3 className="font-pixel text-4xl text-[#fff] tracking-widest mb-6 block">
              !!! SYSTEM CRASH !!!
            </h3>
            <p className="font-code text-2xl text-yellow-300 uppercase mb-10 leading-relaxed">
              {error}
            </p>
            <button
              onClick={reset}
              className="btn-pixel bg-black text-red-500 border-red-500 hover:bg-red-500 hover:text-white w-full text-2xl"
            >
              [ REBOOT SYSTEM ]
            </button>
          </div>
        )}

      </section>

      {/* ─── Footer: Industrial Credits ────────────── */}
      <footer className="w-full max-w-5xl mt-24 pt-10 border-t-8 border-[#222] flex flex-col md:flex-row justify-between items-center gap-8 opacity-40">
        <div className="flex flex-col gap-2">
          <p className="font-pixel text-sm text-[var(--primary)] uppercase tracking-wider">
            [ SPECTRAL WEAVER V5.0 ]
          </p>
          <p className="font-code text-zinc-500 text-sm italic">
            KERNAL STATUS: OPTIMIZED FOR AGENTIC FLOW
          </p>
        </div>
        <div className="flex gap-12 font-code text-xs text-white/20 uppercase tracking-widest">
           <span>Latent-Z: Alpha</span>
           <span>Protocal-X: Active</span>
           <span>Quantum-Link: Secured</span>
        </div>
      </footer>

    </main>
  );
}
