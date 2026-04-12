"use client";

import { useState, useRef } from "react";
import { Upload, FileText, CheckSquare, ChevronRight, AlertTriangle, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface DropZoneProps {
  onFilesSelected: (markdown: File, master: File) => void;
  isProcessing: boolean;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DropZone({ onFilesSelected, isProcessing }: DropZoneProps) {
  const [mdFile, setMdFile] = useState<File | null>(null);
  const [masterFile, setMasterFile] = useState<File | null>(null);
  const [dragOverMd, setDragOverMd] = useState(false);
  const [dragOverMaster, setDragOverMaster] = useState(false);
  const mdInputRef = useRef<HTMLInputElement>(null);
  const masterInputRef = useRef<HTMLInputElement>(null);

  const handleProcess = () => {
    console.log("[TELEMETRY] DropZone handleProcess triggered");
    if (mdFile && masterFile) {
      onFilesSelected(mdFile, masterFile);
    }
  };

  const handleDrop = (e: React.DragEvent, type: "md" | "master") => {
    e.preventDefault();
    setDragOverMd(false);
    setDragOverMaster(false);
    const file = e.dataTransfer.files[0];
    if (!file) return;
    if (type === "md") {
      setMdFile(file);
    } else {
      setMasterFile(file);
    }
  };

  return (
    <div className="flex flex-col gap-10 w-full max-w-4xl mx-auto">
      {/* Markdown Upload */}
      <div
        onClick={() => !isProcessing && mdInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOverMd(true); }}
        onDragLeave={() => setDragOverMd(false)}
        onDrop={(e) => handleDrop(e, "md")}
        className={cn(
          "pixel-box p-12 cursor-pointer flex flex-col md:flex-row items-center gap-8 min-h-[220px] transition-none w-full",
          mdFile 
            ? "pixel-box-primary pixel-box-hover" 
            : dragOverMd 
            ? "pixel-box-primary bg-[#052205]" 
            : "pixel-box-hover",
            isProcessing && "pointer-events-none opacity-50"
        )}
      >
        <input
          type="file"
          className="absolute inset-0 opacity-0 cursor-pointer z-10"
          accept=".md"
          disabled={isProcessing}
          onChange={(e) => {
            console.log("[TELEMETRY] MD Input onChange", e.target.files?.[0]?.name);
            setMdFile(e.target.files?.[0] || null);
          }}
        />

        <div className={cn(
          "w-24 h-24 shrink-0 flex items-center justify-center border-4 border-current bg-black shadow-[4px_4px_0_current]",
          mdFile ? "text-primary" : "text-white/40"
        )}>
          {mdFile ? <CheckSquare className="w-12 h-12" strokeWidth={3} /> : <FileText className="w-12 h-12" strokeWidth={3} />}
        </div>

        <div className="flex-1 text-center md:text-left">
          <h2 className="font-pixel text-2xl md:text-3xl mb-4 text-white uppercase break-all">
            {mdFile ? mdFile.name : "LOAD .MD FILE"}
          </h2>
          <p className="font-code text-xl text-white/50 tracking-widest uppercase">
            {mdFile ? `${formatFileSize(mdFile.size)} - [ LOADED OK ]` : "DRAG & DROP OR CLICK TO SELECT DATA"}
          </p>
        </div>
      </div>

      {/* Master PPTX Upload */}
      <div
        onClick={() => !isProcessing && masterInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOverMaster(true); }}
        onDragLeave={() => setDragOverMaster(false)}
        onDrop={(e) => handleDrop(e, "master")}
        className={cn(
          "pixel-box p-12 cursor-pointer flex flex-col md:flex-row items-center gap-8 min-h-[220px] transition-none w-full",
          masterFile 
            ? "pixel-box-success pixel-box-hover" 
            : dragOverMaster 
            ? "pixel-box-success bg-[#001f1f]" 
            : "pixel-box-hover",
            isProcessing && "pointer-events-none opacity-50"
        )}
      >
        <input
          type="file"
          className="absolute inset-0 opacity-0 cursor-pointer z-10"
          accept=".pptx"
          disabled={isProcessing}
          onChange={(e) => {
            console.log("[TELEMETRY] PPTX Input onChange", e.target.files?.[0]?.name);
            setMasterFile(e.target.files?.[0] || null);
          }}
        />

        <div className={cn(
          "w-24 h-24 shrink-0 flex items-center justify-center border-4 border-current bg-black shadow-[4px_4px_0_current]",
          masterFile ? "text-success" : "text-white/40"
        )}>
          {masterFile ? <CheckSquare className="w-12 h-12" strokeWidth={3} /> : <Upload className="w-12 h-12" strokeWidth={3} />}
        </div>

        <div className="flex-1 text-center md:text-left">
          <h2 className="font-pixel text-2xl md:text-3xl mb-4 text-white uppercase break-all">
            {masterFile ? masterFile.name : "LOAD .PPTX MASTER"}
          </h2>
          <p className="font-code text-xl text-white/50 tracking-widest uppercase">
            {masterFile ? `${formatFileSize(masterFile.size)} - [ LOADED OK ]` : "DRAG & DROP OR CLICK TO INGEST THEME"}
          </p>
        </div>
      </div>

      {/* File size warning */}
      {mdFile && mdFile.size > 5 * 1024 * 1024 && (
        <div className="pixel-box p-6 bg-red-900 border-red-500 w-full flex items-center gap-6">
          <AlertTriangle className="w-10 h-10 text-yellow-400 shrink-0" strokeWidth={3} />
          <p className="font-code text-xl text-yellow-400 uppercase">
            WARNING: DATA EXCEEDS 5MB. TRUNCATION MAY OCCUR.
          </p>
        </div>
      )}

      {/* Launch button */}
      {mdFile && masterFile && !isProcessing && (
        <button
          onClick={handleProcess}
          disabled={isProcessing}
          className={cn(
            "btn-pixel w-full flex items-center justify-center gap-4 text-xl py-8 mt-4",
            isProcessing && "opacity-50 pointer-events-none"
          )}
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-8 h-8 animate-spin" />
              <span>[ SYNCHRONIZING... ]</span>
            </>
          ) : (
            <>
              <span>[ START ENGINE ]</span>
              <ChevronRight className="w-8 h-8" strokeWidth={4} />
            </>
          )}
        </button>
      )}
    </div>
  );
}
