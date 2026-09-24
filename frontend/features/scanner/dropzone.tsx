"use client";

import { ImageUp, X } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";

import { cn, formatBytes } from "@/lib/utils";

const ACCEPT = ["image/png", "image/jpeg", "image/webp", "image/bmp", "image/gif"];
export const MAX_MB = 8;

export function validateImageFile(file: File): string | null {
  if (!ACCEPT.includes(file.type)) return "That file type isn't supported. Use PNG, JPG, WEBP, BMP or GIF.";
  if (file.size > MAX_MB * 1024 * 1024) return `That image is ${formatBytes(file.size)} — the limit is ${MAX_MB} MB.`;
  if (file.size === 0) return "That file is empty.";
  return null;
}

export function Dropzone({
  file, onFile, label, hint, error, onError,
}: {
  file: File | null;
  onFile: (f: File | null) => void;
  label: string;
  hint: string;
  error?: string | null;
  onError: (msg: string | null) => void;
}) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    if (!file) return setPreview(null);
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const accept = useCallback((f: File | undefined | null) => {
    if (!f) return;
    const problem = validateImageFile(f);
    onError(problem);
    if (!problem) onFile(f);
  }, [onFile, onError]);

  // Paste a screenshot straight from the clipboard (Ctrl/Cmd+V) while the zone is visible.
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const item = Array.from(e.clipboardData?.items ?? []).find((i) => i.type.startsWith("image/"));
      if (item) {
        e.preventDefault();
        accept(item.getAsFile());
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [accept]);

  if (file && preview) {
    return (
      <div className="flex items-center gap-4 rounded-sm border border-line-strong bg-surface p-3">
        {/* eslint-disable-next-line @next/next/no-img-element -- local object URL preview */}
        <img src={preview} alt="Selected image preview" className="size-20 rounded-xs border border-line object-cover" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-ink">{file.name || "Pasted image"}</p>
          <p className="font-mono text-xs text-muted">{file.type.replace("image/", "").toUpperCase()} · {formatBytes(file.size)}</p>
          <p className="mt-1 text-xs text-muted">Ready to analyse. The image is processed and not stored.</p>
        </div>
        <button
          type="button"
          onClick={() => onFile(null)}
          className="rounded-sm p-2 text-muted hover:bg-paper-2 hover:text-ink"
          aria-label="Remove image"
        >
          <X className="size-4" />
        </button>
      </div>
    );
  }

  return (
    <div>
      <label
        htmlFor={inputId}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); accept(e.dataTransfer.files?.[0]); }}
        className={cn(
          "flex min-h-44 cursor-pointer flex-col items-center justify-center gap-3 rounded-sm border border-dashed px-6 py-8 text-center transition-colors",
          dragging ? "border-ink bg-paper-2" : "border-line-strong bg-surface-2 hover:border-ink-2 hover:bg-surface",
          error && "border-critical",
        )}
      >
        <span className="grid size-11 place-items-center rounded-full border border-line bg-surface">
          <ImageUp className="size-5 text-ink-2" aria-hidden />
        </span>
        <span>
          <span className="block text-[0.95rem] font-medium text-ink">{label}</span>
          <span className="mt-1 block text-sm text-muted">
            Drag &amp; drop, <span className="underline underline-offset-4">browse</span>, or paste with Ctrl+V
          </span>
        </span>
        <span className="font-mono text-[0.7rem] uppercase tracking-wider text-faint">{hint}</span>
        <input
          id={inputId}
          ref={inputRef}
          type="file"
          accept={ACCEPT.join(",")}
          className="sr-only"
          aria-invalid={!!error}
          onChange={(e) => { accept(e.target.files?.[0]); e.target.value = ""; }}
        />
      </label>
    </div>
  );
}
