"use client";

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { 
  FileText, 
  ChevronRight, 
  Loader2, 
  Move, 
  Maximize2, 
  Trash2, 
  Save, 
  RefreshCw,
  Layout,
  Type,
  CheckSquare,
  Home,
  ArrowUp,
  BarChart3,
  Triangle,
  Filter,
  Activity,
  Undo2
} from "lucide-react";
import { motion, AnimatePresence, useDragControls, DragControls } from "framer-motion";
import { cn } from "@/lib/utils";
import { type SlidePreviewData, api } from "@/lib/api";

interface SlidePreviewProps {
  jobId: string;
  initialSlides: SlidePreviewData[];
  onConfirm: () => void;
  onHome: () => void;
}

// ─── SVG Infographic Components ─────────────────────────────────────────────

const SWOTDiagram = ({ points, colors }: { points: string[], colors: string[] }) => {
  const labels = ["STRENGTHS", "WEAKNESSES", "OPPORTUNITIES", "THREATS"];
  return (
    <div className="grid grid-cols-2 gap-2 w-full h-full p-4">
      {labels.map((label, i) => (
        <div 
          key={i} 
          className="flex flex-col p-3 rounded-sm border border-white/10"
          style={{ backgroundColor: colors[i % colors.length] + '44' }}
        >
          <span className="font-pixel text-[10px] mb-2 opacity-80">{label}</span>
          <p className="font-code text-xs leading-tight">{points[i] || "..."}</p>
        </div>
      ))}
    </div>
  );
};

const FunnelDiagram = ({ stages, colors }: { stages: string[], colors: string[] }) => {
  return (
    <div className="flex flex-col items-center justify-center w-full h-full gap-1 p-4">
      {stages.slice(0, 4).map((stage, i) => {
        const width = 100 - (i * 15);
        return (
          <div 
            key={i}
            className="flex items-center justify-center text-center px-4 font-code text-[10px] uppercase tracking-tighter"
            style={{ 
              width: `${width}%`, 
              height: '25%', 
              backgroundColor: colors[i % colors.length],
              clipPath: 'polygon(0% 0%, 100% 0%, 90% 100%, 10% 100%)'
            }}
          >
            <span className="truncate w-full">{stage}</span>
          </div>
        );
      })}
    </div>
  );
};

const PyramidDiagram = ({ tiers, colors }: { tiers: string[], colors: string[] }) => {
  return (
    <div className="flex flex-col-reverse items-center justify-center w-full h-full gap-1 p-4">
      {tiers.slice(0, 4).map((tier, i) => {
        const width = 100 - (i * 20);
        return (
          <div 
            key={i}
            className="flex items-center justify-center text-center px-4 font-code text-[10px] uppercase tracking-tighter"
            style={{ 
              width: `${width}%`, 
              height: '25%', 
              backgroundColor: colors[i % colors.length],
              clipPath: i === 3 ? 'polygon(50% 0%, 0% 100%, 100% 100%)' : 'polygon(10% 0%, 90% 0%, 100% 100%, 0% 100%)'
            }}
          >
            <span className="truncate w-full">{tier}</span>
          </div>
        );
      })}
    </div>
  );
};

const ChevronFlow = ({ stages, colors }: { stages: string[], colors: string[] }) => {
  return (
    <div className="flex items-center justify-around w-full h-full gap-2 p-6">
      {stages.slice(0, 4).map((stage, i) => (
        <div 
          key={i}
          className="flex-1 h-20 flex items-center justify-center text-center px-4 font-code text-[8px] uppercase font-bold relative"
          style={{ 
            backgroundColor: colors[i % colors.length],
            color: 'black',
            clipPath: 'polygon(0% 0%, 85% 0%, 100% 50%, 85% 100%, 0% 100%, 15% 50%)'
          }}
        >
          {stage}
        </div>
      ))}
    </div>
  );
};

const TimelineDiagram = ({ points, colors }: { points: string[], colors: string[] }) => {
  return (
    <div className="w-full h-full relative p-12">
      <div className="absolute top-1/2 left-8 right-8 h-1 bg-white/10 -translate-y-1/2" />
      <div className="flex items-center justify-between h-full relative z-10">
        {points.slice(0, 4).map((point, i) => {
           const isUp = i % 2 === 0;
           return (
              <div key={i} className="flex flex-col items-center flex-1 relative">
                <div className={cn("absolute flex flex-col items-center w-32", isUp ? "bottom-4" : "top-4")}>
                   <span className="font-code text-[10px] text-center bg-black/60 p-2 border border-white/10 rounded-sm">{point}</span>
                   <div className="w-px h-6 bg-white/20 mt-1" />
                </div>
                <div className="w-4 h-4 rounded-full border-2 border-black" style={{ backgroundColor: colors[i % colors.length] }} />
              </div>
           );
        })}
      </div>
    </div>
  );
};

const AgendaDiagram = ({ points, colors }: { points: string[], colors: string[] }) => {
  return (
    <div className="flex flex-col w-full h-full p-6 justify-center gap-3">
      {points.slice(0, 5).map((point, i) => (
        <div key={i} className="flex items-center gap-4 bg-white/5 p-3 border-l-4" style={{ borderColor: colors[i % colors.length] }}>
            <span className="font-pixel text-xl opacity-20">{i+1}</span>
            <span className="font-code text-xs uppercase tracking-widest truncate">{point}</span>
        </div>
      ))}
    </div>
  );
};

const KeyTakeawayCards = ({ points, colors }: { points: string[], colors: string[] }) => {
  return (
    <div className="flex items-center justify-around w-full h-full gap-4 p-6">
      {points.slice(0, 3).map((point, i) => (
        <div 
           key={i} 
           className="flex-1 h-3/4 bg-black/40 border-t-8 p-4 flex flex-col items-center justify-center text-center gap-4"
           style={{ borderTopColor: colors[i % colors.length] }}
        >
           <Activity size={24} className="opacity-40" style={{ color: colors[i % colors.length] }} />
           <p className="font-code text-[10px] leading-relaxed">{point}</p>
        </div>
      ))}
    </div>
  );
};

const SimpleChart = ({ title, data, colors }: { title: string, data: string[], colors: string[] }) => {
  return (
    <div className="w-full h-full flex flex-col p-4 bg-black/20 rounded-md">
      <div className="flex items-end justify-around flex-1 gap-2 border-b border-white/20 pb-2">
        {data.slice(0, 6).map((point, i) => {
          const height = 30 + (Math.random() * 60); // Simulated visual height
          return (
            <div 
              key={i} 
              className="w-full flex flex-col items-center gap-1"
            >
              <div 
                className="w-full rounded-t-sm" 
                style={{ height: `${height}%`, backgroundColor: colors[i % colors.length] }} 
              />
              <span className="text-[8px] font-code truncate w-full text-center opacity-50">{point.slice(0, 6)}</span>
            </div>
          );
        })}
      </div>
      <span className="font-pixel text-[8px] mt-2 text-center text-white/40 uppercase">{title}</span>
    </div>
  );
};

// ─── DraggableBlock Component ───────────────────────────────────────────────

interface BlockProps {
  id: string;
  type: 'text' | 'graphic';
  content: any;
  defaultStyle: { l: number, t: number, w: number, h: number };
  override: any;
  isActive: boolean;
  isResizing: boolean;
  onSelect: () => void;
  onUpdate: (id: string, delta: any, pushHistory?: boolean) => void;
  onDragEnd: (id: string) => void;
  onResizeStart: (e: React.MouseEvent, id: string, direction: string) => void;
}

const DraggableBlock = ({ 
  id, type, content, defaultStyle, override, isActive, isResizing, 
  onSelect, onUpdate, onDragEnd, onResizeStart 
}: BlockProps) => {
  const dragControls = useDragControls(); // Separate controls for every block

  const x = (override.x ?? defaultStyle.l) * 100;
  const y = (override.y ?? defaultStyle.t) * 100;
  const w = (override.w ?? defaultStyle.w) * 100;
  const h = (override.h ?? defaultStyle.h) * 100;

  return (
    <motion.div
      id={`block-${id}`}
      drag
      dragMomentum={false}
      dragListener={false}
      dragControls={dragControls}
      onDragEnd={() => onDragEnd(id)}
      onClick={(e) => { e.stopPropagation(); onSelect(); }}
      style={{
        position: "absolute",
        left: `${x}%`,
        top: `${y}%`,
        width: `${w}%`,
        minHeight: `${h}%`,
        zIndex: isActive ? 50 : 10,
      }}
      className={cn(
        "group transition-all duration-200",
        isActive ? "ring-2 ring-[var(--accent)] shadow-[0_0_30px_rgba(57,255,20,0.3)]" : "hover:ring-1 hover:ring-white/20"
      )}
    >
      {/* Center Move Handle */}
      {isActive && !isResizing && (
        <div 
          onPointerDown={(e) => dragControls.start(e)}
          className="absolute inset-0 flex items-center justify-center pointer-events-none z-50"
        >
          <div className="w-12 h-12 rounded-full bg-[var(--accent)] text-black flex items-center justify-center shadow-xl cursor-move pointer-events-auto opacity-80 hover:opacity-100 hover:scale-110 transition-all border-4 border-black">
             <Move size={24} />
          </div>
        </div>
      )}

      {/* Resizing Handles */}
      {isActive && (
        <>
          <div 
            onMouseDown={(e) => onResizeStart(e, id, 'se')}
            className="absolute -bottom-2 -right-2 w-4 h-4 bg-white border-2 border-black rounded-sm cursor-nwse-resize z-[60] hover:scale-125 transition-transform"
          />
          <div 
            onMouseDown={(e) => onResizeStart(e, id, 's')}
            className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-4 h-4 bg-white border-2 border-black rounded-sm cursor-ns-resize z-[60] hover:scale-125 transition-transform"
          />
          <div 
            onMouseDown={(e) => onResizeStart(e, id, 'e')}
            className="absolute top-1/2 -right-2 -translate-y-1/2 w-4 h-4 bg-white border-2 border-black rounded-sm cursor-ew-resize z-[60] hover:scale-125 transition-transform"
          />
        </>
      )}

      {/* Delete HUD */}
      {isActive && (
         <button 
           onClick={() => onUpdate(id, { visible: false })} 
           className="absolute -top-4 -right-4 bg-red-600 text-white p-2 rounded-full shadow-lg z-50 hover:bg-red-700 transition-colors"
         >
           <Trash2 size={12} />
         </button>
      )}

      <div className="w-full h-full">
         {type === 'text' ? (
            <div 
              contentEditable 
              suppressContentEditableWarning
              onBlur={(e) => onUpdate(id, { text: e.currentTarget.innerText })}
              className={cn(
                "w-full h-full outline-none",
                id === 'title' ? "text-4xl md:text-5xl font-pixel text-white uppercase" : 
                id === 'summary' ? "text-xl font-code text-[var(--primary)] uppercase" :
                "text-lg font-code text-white/90 whitespace-pre-wrap"
              )}
            >
              {override.text ?? content}
            </div>
         ) : (
           <div className="w-full h-full pointer-events-none">
              {content}
           </div>
         )}
      </div>
    </motion.div>
  );
};

// ─── Main SlidePreview Component ────────────────────────────────────────────

export function SlidePreview({ jobId, initialSlides, onConfirm, onHome }: SlidePreviewProps) {
  const [slides, setSlides] = useState<SlidePreviewData[]>(initialSlides);
  const [history, setHistory] = useState<SlidePreviewData[][]>([]);
  const [current, setCurrent] = useState(0);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isResizing, setIsResizing] = useState(false);

  const canvasRef = useRef<HTMLDivElement>(null);
  const slide = slides[current];
  const accentColors = ["#39FF14", "#FF00FF", "#00FFFF", "#FFFF00"];

  // ─── History Logic ─────────────────────────────────────────────

  const pushToHistory = useCallback((newState: SlidePreviewData[]) => {
    setHistory(prev => {
      const next = [...prev, JSON.parse(JSON.stringify(slides))];
      return next.slice(-2); 
    });
    setSlides(newState);
  }, [slides]);

  const undo = useCallback(() => {
    if (history.length === 0) return;
    const prev = [...history];
    const lastState = prev.pop()!;
    setHistory(prev);
    setSlides(lastState);
  }, [history]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        undo();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo]);

  // ─── Interaction Logic ─────────────────────────────────────────────

  const updateSlideIntent = useCallback(async (newIntent: string) => {
    setSlides(prevSlides => {
      const newSlides = [...prevSlides];
      newSlides[current].visual_intent = newIntent;
      return newSlides;
    });
    
    // Immediate sync to backend
    try {
      await api.syncLayout(jobId, current, slides[current].overrides || {}, newIntent);
    } catch (err) {
      console.error("[STUDIO] Intent sync failed", err);
    }
  }, [current, jobId, slides]);

  const updateSlideOverride = useCallback((componentId: string, delta: Partial<{ x: number, y: number, w: number, h: number, text: string, visible: boolean }>, shouldPushHistory = true) => {
    setSlides(prevSlides => {
      const newSlides = JSON.parse(JSON.stringify(prevSlides));
      const currentOverrides = { ...(newSlides[current].overrides || {}) };
      
      currentOverrides[componentId] = {
        ...(currentOverrides[componentId] || { x: 0.1, y: 0.1, w: 0.5, h: 0.1, visible: true }),
        ...delta
      };
      newSlides[current].overrides = currentOverrides;
      
      if (shouldPushHistory) {
         setHistory(hPrev => [...hPrev, JSON.parse(JSON.stringify(prevSlides))].slice(-2));
      }
      return newSlides;
    });
  }, [current]);

  const handleDragEnd = useCallback((id: string) => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current.getBoundingClientRect();
    const element = document.getElementById(`block-${id}`);
    if (!element) return;
    
    const rect = element.getBoundingClientRect();
    const x = (rect.left - canvas.left) / canvas.width;
    const y = (rect.top - canvas.top) / canvas.height;
    
    updateSlideOverride(id, { x, y });
  }, [updateSlideOverride]);

  const handleResizeStart = (e: React.MouseEvent, id: string, direction: string) => {
    e.stopPropagation();
    e.preventDefault();
    setIsResizing(true);

    const canvas = canvasRef.current?.getBoundingClientRect();
    if (!canvas) return;

    const startX = e.clientX;
    const startY = e.clientY;
    const block = slides[current].overrides?.[id] || { x: 0.1, y: 0.1, w: 0.5, h: 0.1 };
    const startW = block.w;
    const startH = block.h;

    const onMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = (moveEvent.clientX - startX) / canvas.width;
      const deltaY = (moveEvent.clientY - startY) / canvas.height;

      let newW = startW;
      let newH = startH;

      if (direction.includes('e')) newW = Math.max(0.05, startW + deltaX);
      if (direction.includes('s')) newH = Math.max(0.1, startH + deltaY);

      updateSlideOverride(id, { w: newW, h: newH }, false); 
    };

    const onMouseUp = () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      setIsResizing(false);
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  const saveCurrentSlide = async () => {
    setIsSaving(true);
    try {
      await api.syncLayout(jobId, current, slides[current].overrides || {});
    } catch (err) {
      console.error("[STUDIO] Sync failed", err);
    } finally {
      setIsSaving(false);
    }
  };

  const resetSlide = () => {
    setHistory(prev => [...prev, JSON.parse(JSON.stringify(slides))].slice(-2));
    setSlides(prev => {
      const next = [...prev];
      next[current].overrides = {};
      return next;
    });
  };

  const executeExport = async () => {
    setIsExecuting(true);
    try {
      await api.finalize(jobId);
      onConfirm();
    } catch (err: any) {
      console.error("[STUDIO] Finalize failed", err);
      alert(`Finalization Error: ${err.message}`);
      setIsExecuting(false);
    }
  };

  return (
    <div className={cn(
      "w-full flex animate-in fade-in duration-700 relative",
      isFullscreen ? "fixed inset-0 z-[100] bg-black p-0 flex-col" : "max-w-7xl flex-col"
    )}>
      
      {/* Studio Navbar */}
      <div className="flex items-center justify-between border-b-4 border-[#222] bg-black px-8 py-5">
        <div className="flex items-center gap-6">
           <button onClick={onHome} className="text-white/30 hover:text-[var(--accent)] transition-colors">
              <Home size={24} />
           </button>
           <div className="h-8 w-px bg-white/10" />
           <div className="flex flex-col">
              <span className="font-pixel text-xs text-[var(--accent)] tracking-[0.2em] uppercase">Spectral Studio</span>
              <span className="font-code text-[10px] text-zinc-500 uppercase">Interactive Design Stage</span>
           </div>
        </div>
        
        <div className="flex items-center gap-6">
           <button 
             onClick={undo}
             disabled={history.length === 0}
             className={cn(
               "btn-pixel !p-3 !bg-[#111] transition-all",
               history.length === 0 ? "opacity-20 grayscale" : "text-[var(--accent)] hover:scale-110"
             )}
             title="Undo (Ctrl+Z)"
           >
             <Undo2 size={18} />
           </button>

           <div className="h-8 w-px bg-white/10 mx-2" />

           <div className="flex flex-col items-end mr-6">
              <span className="font-pixel text-xs text-white">SLIDE {current + 1} / {slides.length}</span>
              <span className="font-code text-[10px] text-[var(--success)] uppercase tracking-widest">State: Dynamic</span>
           </div>
           <button 
             onClick={() => setIsFullscreen(!isFullscreen)}
             className="btn-pixel !p-3 !bg-[#111] text-white/50 hover:text-white"
           >
             <Maximize2 size={18} />
           </button>
           <button
              onClick={executeExport}
              disabled={isExecuting}
              className="btn-pixel !bg-[var(--success)] !text-black !px-8 py-3 font-pixel text-xs tracking-widest hover:scale-105"
            >
              {isExecuting ? <Loader2 size={16} className="animate-spin" /> : "[ FINALIZE EXPORT ]"}
            </button>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center p-12 bg-[#050505] relative overflow-hidden">
        
        {/* Main Canvas Context */}
        <div 
          ref={canvasRef}
          onClick={() => setSelectedId(null)}
          className="relative w-full aspect-[16/9] max-w-5xl bg-[#111] shadow-[20px_20px_0_0_#000] border-8 border-[#222] overflow-hidden"
        >
          {/* Background Slide Master */}
          {slide.background_url && (
            <img 
              src={api.getSlideImageUrl(slide.background_url)} 
              className="absolute inset-0 w-full h-full object-cover opacity-90 pointer-events-none" 
              alt="Slide Template"
            />
          )}

          {/* Interactive Blocks */}
          <DraggableBlock 
            id="title" type="text" content={slide.title} 
            defaultStyle={{ l: 0.08, t: 0.08, w: 0.8, h: 0.1 }}
            override={slide.overrides?.title || {}}
            isActive={selectedId === 'title'}
            isResizing={isResizing}
            onSelect={() => setSelectedId('title')}
            onUpdate={updateSlideOverride}
            onDragEnd={handleDragEnd}
            onResizeStart={handleResizeStart}
          />

          <DraggableBlock 
            id="summary" type="text" content={slide.summary} 
            defaultStyle={{ l: 0.08, t: 0.22, w: 0.8, h: 0.06 }}
            override={slide.overrides?.summary || {}}
            isActive={selectedId === 'summary'}
            isResizing={isResizing}
            onSelect={() => setSelectedId('summary')}
            onUpdate={updateSlideOverride}
            onDragEnd={handleDragEnd}
            onResizeStart={handleResizeStart}
          />

          <DraggableBlock 
            id="content" type="text" content={slide.data_points.join("\n")} 
            defaultStyle={{ l: 0.08, t: 0.35, w: 0.4, h: 0.4 }}
            override={slide.overrides?.content || {}}
            isActive={selectedId === 'content'}
            isResizing={isResizing}
            onSelect={() => setSelectedId('content')}
            onUpdate={updateSlideOverride}
            onDragEnd={handleDragEnd}
            onResizeStart={handleResizeStart}
          />

          {/* Graphics Blocks */}
          {slide.visual_intent === "swot" && (
            <DraggableBlock 
              id="graphic" type="graphic" content={<SWOTDiagram points={slide.data_points} colors={accentColors} />}
              defaultStyle={{ l: 0.5, t: 0.35, w: 0.4, h: 0.5 }}
              override={slide.overrides?.graphic || {}}
              isActive={selectedId === 'graphic'}
              isResizing={isResizing}
              onSelect={() => setSelectedId('graphic')}
              onUpdate={updateSlideOverride}
              onDragEnd={handleDragEnd}
              onResizeStart={handleResizeStart}
            />
          )}
          {slide.visual_intent === "funnel" && (
            <DraggableBlock 
              id="graphic" type="graphic" content={<FunnelDiagram stages={slide.data_points} colors={accentColors} />}
              defaultStyle={{ l: 0.55, t: 0.3, w: 0.35, h: 0.6 }}
              override={slide.overrides?.graphic || {}}
              isActive={selectedId === 'graphic'}
              isResizing={isResizing}
              onSelect={() => setSelectedId('graphic')}
              onUpdate={updateSlideOverride}
              onDragEnd={handleDragEnd}
              onResizeStart={handleResizeStart}
            />
          )}
          {slide.visual_intent === "pyramid" && (
            <DraggableBlock 
              id="graphic" type="graphic" content={<PyramidDiagram tiers={slide.data_points} colors={accentColors} />}
              defaultStyle={{ l: 0.5, t: 0.3, w: 0.4, h: 0.6 }}
              override={slide.overrides?.graphic || {}}
              isActive={selectedId === 'graphic'}
              isResizing={isResizing}
              onSelect={() => setSelectedId('graphic')}
              onUpdate={updateSlideOverride}
              onDragEnd={handleDragEnd}
              onResizeStart={handleResizeStart}
            />
          )}
          {slide.visual_intent === "chevron-flow" && (
            <DraggableBlock 
              id="graphic" type="graphic" content={<ChevronFlow stages={slide.data_points} colors={accentColors} />}
              defaultStyle={{ l: 0.08, t: 0.6, w: 0.84, h: 0.25 }}
              override={slide.overrides?.graphic || {}}
              isActive={selectedId === 'graphic'}
              isResizing={isResizing}
              onSelect={() => setSelectedId('graphic')}
              onUpdate={updateSlideOverride}
              onDragEnd={handleDragEnd}
              onResizeStart={handleResizeStart}
            />
          )}
          {slide.visual_intent === "timeline" && (
            <DraggableBlock 
              id="graphic" type="graphic" content={<TimelineDiagram points={slide.data_points} colors={accentColors} />}
              defaultStyle={{ l: 0.08, t: 0.5, w: 0.84, h: 0.3 }}
              override={slide.overrides?.graphic || {}}
              isActive={selectedId === 'graphic'}
              isResizing={isResizing}
              onSelect={() => setSelectedId('graphic')}
              onUpdate={updateSlideOverride}
              onDragEnd={handleDragEnd}
              onResizeStart={handleResizeStart}
            />
          )}
          {slide.visual_intent === "agenda" && (
            <DraggableBlock 
              id="graphic" type="graphic" content={<AgendaDiagram points={slide.data_points} colors={accentColors} />}
              defaultStyle={{ l: 0.3, t: 0.2, w: 0.4, h: 0.6 }}
              override={slide.overrides?.graphic || {}}
              isActive={selectedId === 'graphic'}
              isResizing={isResizing}
              onSelect={() => setSelectedId('graphic')}
              onUpdate={updateSlideOverride}
              onDragEnd={handleDragEnd}
              onResizeStart={handleResizeStart}
            />
          )}
          {slide.visual_intent === "key-takeaways" && (
            <DraggableBlock 
              id="graphic" type="graphic" content={<KeyTakeawayCards points={slide.data_points} colors={accentColors} />}
              defaultStyle={{ l: 0.1, t: 0.4, w: 0.8, h: 0.4 }}
              override={slide.overrides?.graphic || {}}
              isActive={selectedId === 'graphic'}
              isResizing={isResizing}
              onSelect={() => setSelectedId('graphic')}
              onUpdate={updateSlideOverride}
              onDragEnd={handleDragEnd}
              onResizeStart={handleResizeStart}
            />
          )}
          {(slide.has_chart || slide.visual_intent === "chart-bar") && (
            <DraggableBlock 
              id="graphic" type="graphic" content={<SimpleChart title={slide.visual_intent} data={slide.data_points} colors={accentColors} />}
              defaultStyle={{ l: 0.5, t: 0.35, w: 0.45, h: 0.5 }}
              override={slide.overrides?.graphic || {}}
              isActive={selectedId === 'graphic'}
              isResizing={isResizing}
              onSelect={() => setSelectedId('graphic')}
              onUpdate={updateSlideOverride}
              onDragEnd={handleDragEnd}
              onResizeStart={handleResizeStart}
            />
          )}

          {/* Overlay Grid */}
          <div className="absolute inset-0 pointer-events-none opacity-[0.05] bg-[linear-gradient(to_right,#FFF_1px,transparent_1px),linear-gradient(to_bottom,#FFF_1px,transparent_1px)] bg-[size:40px_40px]" />
        </div>

        {/* Floating Quick Action Bar */}
        <div className="absolute top-1/2 -right-20 -translate-y-1/2 flex flex-col gap-4 opacity-40 hover:opacity-100 transition-opacity">
           {/* Intent Switcher Trigger */}
           <div className="relative group/intent">
              <button className="btn-pixel !p-4 !bg-[var(--accent)] !text-black shadow-[0_0_20px_var(--accent-glow)]" title="Change Diagram Type">
                 <Layout size={20} />
              </button>
              <div className="absolute right-full mr-4 top-0 w-64 bg-black border-4 border-[#222] p-4 hidden group-hover/intent:block animate-in slide-in-from-right-2 duration-200 z-[100]">
                 <p className="font-pixel text-[8px] text-white/40 mb-4 uppercase">Select Visual Intent</p>
                 <div className="grid grid-cols-2 gap-2">
                    {[
                      { id: "bullet-points", label: "Bullets", icon: Type },
                      { id: "chevron-flow", label: "Process", icon: ChevronRight },
                      { id: "funnel", label: "Funnel", icon: Filter },
                      { id: "pyramid", label: "Pyramid", icon: Triangle },
                      { id: "timeline", label: "Timeline", icon: RefreshCw },
                      { id: "swot", label: "SWOT", icon: Layout },
                      { id: "chart-bar", label: "Charts", icon: BarChart3 },
                      { id: "agenda", label: "Agenda", icon: FileText },
                      { id: "key-takeaways", label: "Takeaway", icon: CheckSquare },
                    ].map((intent) => (
                       <button
                         key={intent.id}
                         onClick={() => updateSlideIntent(intent.id)}
                         className={cn(
                           "flex flex-col items-center gap-2 p-2 border-2 border-white/5 hover:border-[var(--primary)] hover:bg-[var(--primary)]/10 transition-all",
                           slide.visual_intent === intent.id && "border-[var(--primary)] bg-[var(--primary)]/10"
                         )}
                       >
                         <intent.icon size={16} className={cn(slide.visual_intent === intent.id ? "text-[var(--primary)]" : "text-white/40")} />
                         <span className="font-code text-[8px] uppercase">{intent.label}</span>
                       </button>
                    ))}
                 </div>
              </div>
           </div>

           <button onClick={saveCurrentSlide} className="btn-pixel !p-4 !bg-black" title="Save Layout">
              {isSaving ? <Loader2 className="animate-spin" /> : <Save size={20} />}
           </button>
           <button onClick={resetSlide} className="btn-pixel !p-4 !bg-black text-red-500" title="Reset Slide">
              <RefreshCw size={20} />
           </button>
           <button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} className="btn-pixel !p-4 !bg-black" title="Back to Top">
              <ArrowUp size={20} />
           </button>
        </div>
      </div>

      {/* Bottom Filmstrip Gallery */}
      <div className="w-full bg-black border-t-4 border-[#222] p-6 pb-10">
        <div className="flex items-center gap-6 mb-4">
           <span className="font-pixel text-[10px] text-white/30 uppercase tracking-[0.2em]">Filmstrip Sequence</span>
           <div className="h-px flex-1 bg-white/5" />
        </div>
        
        <div className="flex gap-4 overflow-x-auto pb-4 custom-scrollbar">
           {slides.map((s, idx) => (
             <motion.button
               key={idx}
               whileHover={{ scale: 1.05 }}
               whileTap={{ scale: 0.95 }}
               onClick={() => setCurrent(idx)}
               className={cn(
                 "relative flex-shrink-0 w-48 aspect-[16/9] border-4 transition-all overflow-hidden group",
                 current === idx 
                   ? "border-[var(--accent)] shadow-[0_0_20px_var(--accent-glow)] scale-105" 
                   : "border-[#333] grayscale opacity-40 hover:opacity-100 hover:grayscale-0"
               )}
             >
               {s.background_url && (
                 <img 
                    src={api.getSlideImageUrl(s.background_url)} 
                    className="w-full h-full object-cover" 
                    alt={`Slide ${idx+1}`} 
                 />
               )}
               <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity">
                  <span className="font-pixel text-xl text-white">{idx + 1}</span>
               </div>
               <div className="absolute bottom-2 left-2 flex gap-1">
                  {s.visual_intent !== "BULLET_POINTS" && <Activity size={10} className="text-[var(--accent)]" />}
                  {s.has_chart && <BarChart3 size={10} className="text-[var(--primary)]" />}
               </div>
             </motion.button>
           ))}
        </div>
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          height: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #000;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #333;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: var(--accent);
        }
      `}</style>
    </div>
  );
}
