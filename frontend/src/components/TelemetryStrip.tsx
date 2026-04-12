"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";

const STAGES = [
  { id: "ingest", label: "DATA INGESTION" },
  { id: "storyliner", label: "STORYLINE PARSING" },
  { id: "blueprint", label: "BLUEPRINT GENERATION" },
  { id: "theme", label: "THEMING INTEGRATION" },
  { id: "render", label: "RENDER ENGINE" },
  { id: "validate", label: "QA CHECKSUM" },
];

interface TelemetryStripProps {
  stages: Record<string, "started" | "completed">;
  currentStage: string;
}

export function TelemetryStrip({ stages, currentStage }: TelemetryStripProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  const completedCount = Object.values(stages).filter((s) => s === "completed").length;
  const progress = Math.round((completedCount / STAGES.length) * 100);

  return (
    <div className="w-full max-w-4xl pixel-box p-8 md:p-12 mb-10 flex flex-col">
      <div className="flex items-center justify-between mb-8 border-b-4 border-[var(--border-color)] pb-4">
        <h3 className="font-pixel text-xl text-white">SYSTEM_LOG //</h3>
        <span className="font-code text-2xl text-[var(--primary)] uppercase border-2 border-[var(--primary)] px-4 py-1">
          {elapsed} SEC
        </span>
      </div>

      <div className="flex flex-col gap-4 font-code text-xl uppercase">
        {STAGES.map((stage) => {
          const status = stages[stage.id];
          const isActive = currentStage === stage.id;
          const isDone = status === "completed";

          return (
            <div key={stage.id} className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-l-4 border-[#333] pl-4">
              <span className={cn(
                "transition-colors",
                isDone ? "text-white/60" : isActive ? "text-[var(--primary)]" : "text-[#555]"
              )}>
                {">"} {stage.label}
              </span>
              
              <span className={cn(
                "font-pixel text-sm tracking-widest px-3 py-1",
                isDone 
                  ? "bg-success text-black" 
                  : isActive 
                  ? "bg-primary text-black animate-pulse" 
                  : "bg-[#222] text-[#666]"
              )}>
                {isDone ? "[ OK ]" : isActive ? "[ EXEC ]" : "[ WAIT ]"}
              </span>
            </div>
          );
        })}
      </div>

      <div className="mt-12 w-full h-8 bg-black border-4 border-[#333] relative">
        <div 
          className="h-full bg-primary transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
        <div className="absolute inset-0 flex items-center justify-center font-pixel text-xs text-white mix-blend-difference">
          LOADING {progress}%
        </div>
      </div>
    </div>
  );
}
