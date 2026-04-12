"use client";

import { useState, useEffect, useRef } from "react";
import { TemplateMeta, api } from "@/lib/api";
import { Loader2 } from "lucide-react";

interface TemplateSelectorProps {
  onSelect: (templateId: string) => void;
  isProcessing: boolean;
}

export function TemplateSelector({ onSelect, isProcessing }: TemplateSelectorProps) {
  const [templates, setTemplates] = useState<TemplateMeta[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [currentSlideIdx, setCurrentSlideIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getTemplates();
        setTemplates(data);

        // If any template has no slide images, trigger thumbnail generation
        const needsGen = data.some((t) => !t.slide_images || t.slide_images.length === 0);
        if (needsGen) {
          setGenerating(true);
          try {
            await api.generateThumbnails();
            const refreshed = await api.getTemplates();
            setTemplates(refreshed);
          } catch (err) {
            console.error("Thumbnail generation failed:", err);
          } finally {
            setGenerating(false);
          }
        }
      } catch (err) {
        console.error("Failed to fetch templates:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Scroll to top/reset slide index when switching templates
  useEffect(() => {
    setCurrentSlideIdx(0);
  }, [currentIdx]);

  const nextTemplate = () => {
    if (templates.length === 0) return;
    setCurrentIdx((p) => (p + 1) % templates.length);
  };
  const prevTemplate = () => {
    if (templates.length === 0) return;
    setCurrentIdx((p) => (p - 1 + templates.length) % templates.length);
  };

  const nextSlide = () => {
    const tmpl = templates[currentIdx];
    const total = tmpl.slide_images?.length || tmpl.layouts.length;
    setCurrentSlideIdx((p) => (p + 1) % total);
  };
  const prevSlide = () => {
    const tmpl = templates[currentIdx];
    const total = tmpl.slide_images?.length || tmpl.layouts.length;
    setCurrentSlideIdx((p) => (p - 1 + total) % total);
  };

  // ─── Loading state ──────────────────────────────────────────────
  if (loading) {
    return (
      <div className="pixel-box p-16 bg-[#111] flex flex-col items-center justify-center gap-6">
        <Loader2 className="w-12 h-12 text-[var(--accent)] animate-spin" />
        <span className="font-code text-lg text-[var(--accent)]">[ SYNCING MASTER REPOSITORY... ]</span>
      </div>
    );
  }

  if (templates.length === 0) {
    return (
      <div className="pixel-box p-16 bg-[#111] text-center">
        <span className="font-pixel text-xl text-red-500">[ NO TEMPLATES FOUND ]</span>
        <p className="font-code text-sm text-white/40 mt-4">Ensure templates_meta.json and slide master directory exist.</p>
      </div>
    );
  }

  const tmpl = templates[currentIdx];
  const hasImages = tmpl.slide_images && tmpl.slide_images.length > 0;
  const shortName = tmpl.id.replace(/^Template_/, "").replace(/_/g, " ");
  const totalSlides = tmpl.slide_images?.length || tmpl.layouts.length;

  return (
    <div className="w-full flex flex-col gap-8">

      {/* ─── Header: Template name + indicators ─── */}
      <div className="flex flex-col md:flex-row justify-between items-center gap-6 border-b-4 border-[#222] pb-6">
        <div className="flex flex-col gap-2">
          <label className="font-pixel text-[10px] text-white/40 uppercase tracking-widest">
            [ STAGE 2: MASTER SELECTION ]
          </label>
          <div className="flex items-center gap-4 flex-wrap">
            <h2 className="font-pixel text-xl md:text-2xl text-[var(--accent)] uppercase leading-tight">
              {shortName}
            </h2>
            <div className="flex gap-2">
              {templates.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentIdx(i)}
                  className={`w-3 h-3 border-2 transition-all ${
                    i === currentIdx
                      ? "bg-[var(--accent)] border-[var(--accent)] scale-125"
                      : "border-white/20 hover:border-white/40"
                  }`}
                />
              ))}
            </div>
          </div>
          <span className="font-code text-[10px] text-white/30">
            THEME {currentIdx + 1}/{templates.length} // SLIDE {currentSlideIdx + 1}/{totalSlides}
          </span>
        </div>

        <button
          onClick={() => onSelect(tmpl.id)}
          disabled={isProcessing}
          className="btn-pixel bg-[var(--primary)] text-black px-10 py-4 text-xl !shadow-[6px_6px_0_0_#FFF] hover:scale-105 transition-transform"
        >
          {isProcessing ? "[ WEAVING... ]" : "[ ACTIVATE MASTER ]"}
        </button>
      </div>

      {/* ─── Orbital Stage (Horizontal Carousel) ─── */}
      <div className={`relative overflow-hidden bg-[#0a0a0a] border-8 transition-all duration-300 min-h-[500px] flex items-center justify-center ${
        tmpl.id ? "border-[var(--primary)] shadow-[0_0_30px_rgba(57,255,20,0.3)]" : "border-[#1a1a1a]"
      }`}>

        {/* Template Controls (<<  >>) */}
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 flex justify-between z-40 px-6 pointer-events-none">
          <button
            onClick={prevTemplate}
            className="btn-pixel bg-black/90 text-[var(--accent)] text-4xl px-6 py-4 pointer-events-auto hover:scale-110 !border-[var(--accent)] shadow-[4px_4px_0_0_#000]"
            title="Previous Master"
          >
            {"<<"}
          </button>
          <button
            onClick={nextTemplate}
            className="btn-pixel bg-black/90 text-[var(--accent)] text-4xl px-6 py-4 pointer-events-auto hover:scale-110 !border-[var(--accent)] shadow-[4px_4px_0_0_#000]"
            title="Next Master"
          >
            {">>"}
          </button>
        </div>

        {/* Slide Controls (<  >) */}
        <div className="absolute inset-x-0 bottom-10 flex justify-center gap-10 z-40 px-6 pointer-events-none">
          <button
            onClick={prevSlide}
            className="btn-pixel bg-black/80 text-[var(--primary)] text-2xl px-6 py-3 pointer-events-auto hover:text-white !border-[var(--primary)] shadow-[4px_4px_0_0_#000]"
          >
            {"< PREV"}
          </button>
          <button
            onClick={nextSlide}
            className="btn-pixel bg-black/80 text-[var(--primary)] text-2xl px-6 py-3 pointer-events-auto hover:text-white !border-[var(--primary)] shadow-[4px_4px_0_0_#000]"
          >
            {"NEXT >"}
          </button>
        </div>

        {/* Viewport for the current slide */}
        <div
          key={`${currentIdx}-${currentSlideIdx}`}
          className="w-full flex justify-center items-center py-16 px-24 animate-slide-in"
        >
          {generating && (
            <div className="flex flex-col items-center gap-4 py-16">
              <Loader2 className="w-10 h-10 text-[var(--accent)] animate-spin" />
              <span className="font-pixel text-sm text-[var(--accent)]">[ RENDERING SLIDE THUMBNAILS... ]</span>
            </div>
          )}

          {!generating && hasImages && tmpl.slide_images[currentSlideIdx] && (
            <div className="w-full max-w-4xl relative group">
              <div className="absolute -top-6 left-0 z-10 bg-[var(--primary)] text-black font-pixel text-xs px-4 py-1 shadow-[4px_4px_0_0_#000]">
                MASTER PREVIEW: SLIDE {currentSlideIdx + 1}
              </div>
              
              <img
                src={api.getSlideImageUrl(tmpl.slide_images[currentSlideIdx])}
                alt={`Slide ${currentSlideIdx + 1}`}
                className="w-full aspect-[16/9] object-contain bg-black border-4 border-white/10 group-hover:border-[var(--primary)] transition-all shadow-[0_20px_50px_rgba(0,0,0,0.8)]"
              />
              
              {tmpl.layouts[currentSlideIdx] && (
                <div className="mt-4 text-center">
                  <span className="font-code text-sm text-white/50 bg-black/50 px-4 py-1 border border-white/10">
                    LAYOUT: {tmpl.layouts[currentSlideIdx].name}
                  </span>
                </div>
              )}
            </div>
          )}

          {!generating && !hasImages && tmpl.layouts[currentSlideIdx] && (
                <div className="w-full max-w-4xl aspect-[16/9] bg-[#0c0c0c] border-4 border-white/10 p-12 flex flex-col gap-6 relative shadow-[0_20px_50px_rgba(0,0,0,0.8)]">
                  <div className="absolute top-4 left-4 font-pixel text-sm text-[var(--accent)]">SCHEMATIC: SLIDE {currentSlideIdx + 1}</div>
                  <div className="absolute top-4 right-4 font-code text-sm text-white/40">{tmpl.layouts[currentSlideIdx].name}</div>
                  <div className="flex-1 flex flex-col justify-center items-center gap-6 opacity-30">
                    <div className="w-3/4 h-12 bg-[var(--accent)] opacity-40 shadow-[0_0_20px_var(--accent)]" />
                    <div className="w-2/3 h-6 bg-white/20" />
                    <div className="w-1/2 h-6 bg-white/10" />
                  </div>
                </div>
          )}
        </div>
      </div>

      <style jsx>{`
        @keyframes slide-in {
          0% { opacity: 0; transform: translateX(50px); filter: blur(10px); }
          100% { opacity: 1; transform: translateX(0); filter: blur(0); }
        }
        .animate-slide-in {
          animation: slide-in 0.4s cubic-bezier(0.22, 1, 0.36, 1);
        }
        div::-webkit-scrollbar { width: 4px; }
        div::-webkit-scrollbar-track { background: transparent; }
        div::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
      `}</style>
    </div>
  );
}
