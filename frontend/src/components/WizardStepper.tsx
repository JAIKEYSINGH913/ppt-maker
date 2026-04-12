"use client";

import { cn } from "@/lib/utils";

interface WizardStepperProps {
  currentStep: number; // 0=Upload, 1=Processing/Preview, 2=Download
}

const STEPS = [
  { id: "STAGE 1", label: "DATA INGEST" },
  { id: "STAGE 2", label: "MASTER SECT" },
  { id: "STAGE 3", label: "PROCESSING" },
  { id: "STAGE 4", label: "PREVIEW" },
  { id: "STAGE 5", label: "EXPORT" },
];

export function WizardStepper({ currentStep }: WizardStepperProps) {
  return (
    <div className="w-full max-w-4xl mx-auto mb-16 px-4">
      <div className="flex flex-col md:flex-row w-full gap-4">
        {STEPS.map((step, idx) => {
          const isActive = idx === currentStep;
          const isDone = idx < currentStep;

          return (
            <div 
              key={idx} 
              className={cn(
                "flex-1 flex items-center p-4 border-4 transition-all",
                isDone 
                  ? "bg-success text-black border-success box-shadow-[4px_4px_0_rgba(0,255,255,0.4)]"
                  : isActive
                  ? "bg-primary text-black border-primary box-shadow-[4px_4px_0_rgba(57,255,20,0.5)] scale-105 z-10 animate-pulse origin-left"
                  : "bg-black text-[#555] border-[#333] shadow-[4px_4px_0_#222]"
              )}
            >
              <div className="font-pixel text-sm md:text-xs lg:text-sm uppercase tracking-widest w-full text-center">
                <span className="block mb-2 opacity-60 text-xs">{step.id}</span>
                {step.label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
