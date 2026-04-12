const API_BASE_URL = "http://127.0.0.1:8000";

export type PipelineStage = 
  | "ingest" 
  | "storyliner" 
  | "blueprint" 
  | "theme" 
  | "render" 
  | "validate";

export type JobStatus = {
  id: string;
  status: "processing" | "completed" | "failed";
  current_stage: string;
  stages: Record<string, "started" | "completed">;
  output_filename: string;
  slide_count: number;
  error?: string;
};

export type SlidePreviewData = {
  index: number;
  title: string;
  summary: string;
  visual_intent: string;
  data_points: string[];
  icon_tokens: string[];
  layout_hint: string;
  has_chart: boolean;
  has_table: boolean;
  overrides?: Record<string, any>; // User-defined layout and text adjustments
};

export type TemplateLayout = {
  index: number;
  name: string;
  placeholders: string[];
};

export type TemplateMeta = {
  id: string;
  filename: string;
  layouts: TemplateLayout[];
  count: number;
  slide_images: string[];   // URLs for actual slide thumbnails
};

export type PreviewResponse = {
  slides: SlidePreviewData[];
  total: number;
  message?: string;
};

export const api = {
  async process(markdown: File, masterOrId: File | string) {
    const formData = new FormData();
    formData.append("markdown_file", markdown);
    
    if (typeof masterOrId === "string") {
      formData.append("template_id", masterOrId);
    } else {
      formData.append("master_file", masterOrId);
    }

    const response = await fetch(`${API_BASE_URL}/process`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) throw new Error("Failed to start processing");
    return (await response.json()) as { job_id: string };
  },

  async getTemplates() {
    const response = await fetch(`${API_BASE_URL}/templates`);
    if (!response.ok) throw new Error("Failed to load templates");
    return (await response.json()) as TemplateMeta[];
  },

  async generateThumbnails() {
    const response = await fetch(`${API_BASE_URL}/templates/generate-thumbnails`, {
      method: "POST",
    });
    if (!response.ok) throw new Error("Failed to generate thumbnails");
    return await response.json();
  },

  async getStatus(jobId: string) {
    const response = await fetch(`${API_BASE_URL}/status/${jobId}`);
    if (!response.ok) throw new Error("Failed to get status");
    return (await response.json()) as JobStatus;
  },

  async getPreview(jobId: string) {
    const response = await fetch(`${API_BASE_URL}/preview/${jobId}`);
    if (!response.ok) throw new Error("Failed to get preview");
    return (await response.json()) as PreviewResponse;
  },

  async getSlidePreview(jobId: string, index: number) {
    const response = await fetch(`${API_BASE_URL}/preview/${jobId}/slide/${index}`);
    if (!response.ok) throw new Error("Failed to get slide preview");
    return (await response.json()) as SlidePreviewData;
  },

  async syncLayout(jobId: string, index: number, overrides: Record<string, any>, visualIntent?: string) {
    const response = await fetch(`${API_BASE_URL}/sync-layout/${jobId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index, overrides, visual_intent: visualIntent }),
    });
    if (!response.ok) throw new Error("Failed to sync layout");
    return await response.json();
  },

  async finalize(jobId: string) {
    const response = await fetch(`${API_BASE_URL}/finalize/${jobId}`, {
      method: "POST",
    });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to finalize job");
    }
    return await response.json();
  },

  getDownloadUrl(jobId: string) {
    return `${API_BASE_URL}/download/${jobId}`;
  },

  downloadExport(jobId: string) {
    window.open(`${API_BASE_URL}/download/${jobId}`, "_blank");
  },

  getManifestUrl(jobId: string) {
    return `${API_BASE_URL}/manifest/${jobId}`;
  },

  /** Build full URL for a slide thumbnail image */
  getSlideImageUrl(relativePath: string) {
    return `${API_BASE_URL}${relativePath}`;
  },
};
