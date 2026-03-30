"use client";

import { useState, useCallback, useRef } from "react";
import { useI18n } from "@/hooks/use-i18n";

interface UploadZoneProps {
  onFilesUploaded: (fileNames: string[]) => void;
  autoProcess: boolean;
  onAutoProcessChange: (v: boolean) => void;
}

export function UploadZone({ onFilesUploaded, autoProcess, onAutoProcessChange }: UploadZoneProps) {
  const { t } = useI18n();
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<string>("");
  const dragCountRef = useRef(0);

  const uploadFiles = useCallback(
    async (fileList: FileList | File[] | null) => {
      if (!fileList) return;
      const allFiles = Array.from(fileList);
      const pdfFiles = allFiles.filter((f) =>
        f.name.toLowerCase().endsWith(".pdf") || f.type === "application/pdf"
      );
      if (pdfFiles.length === 0) {
        setStatus(`${t("invoice.noPdf")} (${allFiles.length} ${t("invoice.filesInFolder")})`);
        setTimeout(() => setStatus(""), 5000);
        return;
      }

      setUploading(true);
      const totalCount = pdfFiles.length;
      const allUploaded: string[] = [];
      const BATCH_SIZE = 5;

      try {
        for (let i = 0; i < pdfFiles.length; i += BATCH_SIZE) {
          const batch = pdfFiles.slice(i, i + BATCH_SIZE);
          setStatus(`${t("invoice.uploadProgress")} ${Math.min(i + BATCH_SIZE, totalCount)}/${totalCount} ${t("invoice.uploadPdf")}`);

          const formData = new FormData();
          for (const f of batch) formData.append("files", f);

          const res = await fetch("/api/documents/upload", {
            method: "POST",
            body: formData,
          });

          if (!res.ok) continue;

          let data: { files?: string[]; error?: string };
          try {
            data = await res.json();
          } catch {
            continue;
          }

          if (data.files?.length) {
            allUploaded.push(...data.files);
          }
        }

        if (allUploaded.length > 0) {
          setStatus(`+${allUploaded.length} ${t("invoice.uploadDone")}`);
          onFilesUploaded(allUploaded);
        } else {
          setStatus(t("invoice.uploadZeroSuccess"));
        }
      } catch {
        setStatus(t("invoice.uploadFailed"));
      } finally {
        setUploading(false);
        setTimeout(() => setStatus(""), 4000);
      }
    },
    [onFilesUploaded, t]
  );

  const handleBrowseFiles = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf";
    input.multiple = true;
    input.onchange = () => uploadFiles(input.files);
    input.click();
  }, [uploadFiles]);

  const handleBrowseFolder = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    input.setAttribute("webkitdirectory", "");
    input.onchange = () => uploadFiles(input.files);
    input.click();
  }, [uploadFiles]);

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
          <span className="text-primary font-medium animate-pulse">{t("invoice.uploading")}</span>
        ) : isDragging ? (
          <span className="text-primary font-medium">{t("invoice.dropHere")}</span>
        ) : (
          <>
            <span className="text-muted-foreground">{t("invoice.dragPdf")}</span>
            <span className="text-muted-foreground/30">|</span>
            <button type="button" onClick={handleBrowseFiles} className="text-primary hover:underline text-sm font-medium">
              {t("invoice.browseFiles")}
            </button>
            <span className="text-muted-foreground/30">|</span>
            <button type="button" onClick={handleBrowseFolder} className="text-primary hover:underline text-sm font-medium">
              {t("invoice.browseFolder")}
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
          {t("invoice.autoProcess")}
        </label>
        {status && (
          <span className={`text-xs font-medium ${status.startsWith("+") ? "text-green-600" : status.includes("0") || status.toLowerCase().includes("fail") || status.toLowerCase().includes("hiba") ? "text-red-600" : "text-blue-600"}`}>
            {status}
          </span>
        )}
      </div>
    </div>
  );
}
