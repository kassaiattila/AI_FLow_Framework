"use client";

import { useState, useCallback, useRef } from "react";

interface UploadZoneProps {
  onFilesUploaded: (fileNames: string[]) => void;
  autoProcess: boolean;
  onAutoProcessChange: (v: boolean) => void;
}

export function UploadZone({ onFilesUploaded, autoProcess, onAutoProcessChange }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<string>("");
  const dragCountRef = useRef(0);

  const uploadFiles = useCallback(
    async (fileList: FileList | File[] | null) => {
      if (!fileList) return;
      const allFiles = Array.from(fileList);
      console.log(`[UploadZone] Total files received: ${allFiles.length}`);
      allFiles.slice(0, 5).forEach((f, i) =>
        console.log(`  [${i}] name="${f.name}" type="${f.type}" size=${f.size}`)
      );
      const pdfFiles = allFiles.filter((f) =>
        f.name.toLowerCase().endsWith(".pdf") || f.type === "application/pdf"
      );
      console.log(`[UploadZone] PDF files after filter: ${pdfFiles.length}`);
      if (pdfFiles.length === 0) {
        setStatus(`Nincs PDF (${allFiles.length} fajl a mappaban, de 0 PDF)`);
        setTimeout(() => setStatus(""), 5000);
        return;
      }

      setUploading(true);
      const totalCount = pdfFiles.length;
      const allUploaded: string[] = [];
      const BATCH_SIZE = 5; // Upload in batches to avoid body size limits

      try {
        for (let i = 0; i < pdfFiles.length; i += BATCH_SIZE) {
          const batch = pdfFiles.slice(i, i + BATCH_SIZE);
          setStatus(`Feltoltes: ${Math.min(i + BATCH_SIZE, totalCount)}/${totalCount} PDF...`);

          const formData = new FormData();
          for (const f of batch) formData.append("files", f);

          const res = await fetch("/api/documents/upload", {
            method: "POST",
            body: formData,
          });

          if (!res.ok) {
            const text = await res.text();
            console.error(`Upload batch failed (${res.status}):`, text);
            continue;
          }

          let data: { files?: string[]; error?: string };
          try {
            data = await res.json();
          } catch {
            console.error("Upload response not JSON");
            continue;
          }

          console.log(`[UploadZone] Batch response:`, data);
          if (data.files?.length) {
            allUploaded.push(...data.files);
          }
        }

        if (allUploaded.length > 0) {
          setStatus(`+${allUploaded.length} fajl feltoltve`);
          onFilesUploaded(allUploaded);
        } else {
          setStatus("Hiba: 0 fajl sikerult feltolteni");
        }
      } catch (err) {
        setStatus("Feltoltes sikertelen");
        console.error("Upload failed:", err);
      } finally {
        setUploading(false);
        setTimeout(() => setStatus(""), 4000);
      }
    },
    [onFilesUploaded]
  );

  // File input: browse for files
  const handleBrowseFiles = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf";
    input.multiple = true;
    input.onchange = () => uploadFiles(input.files);
    input.click();
  }, [uploadFiles]);

  // Folder input: browse for folder
  const handleBrowseFolder = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    input.setAttribute("webkitdirectory", "");
    input.onchange = () => uploadFiles(input.files);
    input.click();
  }, [uploadFiles]);

  // Drag & drop
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCountRef.current = 0;
      setIsDragging(false);
      uploadFiles(e.dataTransfer.files);
    },
    [uploadFiles]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCountRef.current++;
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCountRef.current--;
    if (dragCountRef.current <= 0) {
      dragCountRef.current = 0;
      setIsDragging(false);
    }
  }, []);

  return (
    <div
      className={`rounded-lg border-2 border-dashed px-4 py-3 text-center transition-colors ${
        isDragging
          ? "border-primary bg-primary/5 ring-2 ring-primary/20"
          : "border-muted-foreground/20 hover:border-muted-foreground/40"
      }`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
    >
      <div className="flex items-center justify-center gap-3 text-sm">
        {uploading ? (
          <span className="text-primary font-medium animate-pulse">Feltoltes folyamatban...</span>
        ) : isDragging ? (
          <span className="text-primary font-medium">Engedd el a fajlokat ide...</span>
        ) : (
          <>
            <span className="text-muted-foreground">Huzd ide a PDF fajlokat</span>
            <span className="text-muted-foreground/30">|</span>
            <button
              type="button"
              onClick={handleBrowseFiles}
              className="text-primary hover:underline text-sm font-medium"
            >
              Tallozas
            </button>
            <span className="text-muted-foreground/30">|</span>
            <button
              type="button"
              onClick={handleBrowseFolder}
              className="text-primary hover:underline text-sm font-medium"
            >
              Mappa
            </button>
          </>
        )}
      </div>

      <div className="mt-1.5 flex items-center justify-center gap-4">
        <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer">
          <input
            type="checkbox"
            checked={autoProcess}
            onChange={(e) => onAutoProcessChange(e.target.checked)}
            className="size-3.5 rounded border-border accent-primary"
          />
          Auto feldolgozas feltoltes utan
        </label>
        {status && (
          <span className={`text-xs font-medium ${status.startsWith("+") ? "text-green-600" : status.startsWith("Hiba") || status.startsWith("Nincs") || status.startsWith("Feltoltes s") ? "text-red-600" : "text-blue-600"}`}>
            {status}
          </span>
        )}
      </div>
    </div>
  );
}
