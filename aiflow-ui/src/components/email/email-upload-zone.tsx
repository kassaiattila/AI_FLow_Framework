"use client";

import { useState, useCallback, useRef } from "react";
import { useI18n } from "@/hooks/use-i18n";

interface EmailUploadZoneProps {
  onFilesUploaded: (fileNames: string[]) => void;
}

const ACCEPTED_EXTENSIONS = [".eml", ".msg", ".txt"];

export function EmailUploadZone({ onFilesUploaded }: EmailUploadZoneProps) {
  const { t } = useI18n();
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<string>("");
  const dragCountRef = useRef(0);

  const uploadFiles = useCallback(
    async (fileList: FileList | File[] | null) => {
      if (!fileList) return;
      const allFiles = Array.from(fileList);
      const emailFiles = allFiles.filter((f) =>
        ACCEPTED_EXTENSIONS.some((ext) => f.name.toLowerCase().endsWith(ext))
      );

      if (emailFiles.length === 0) {
        setStatus(t("email.uploadNoFiles"));
        setTimeout(() => setStatus(""), 5000);
        return;
      }

      setUploading(true);
      setStatus(`${t("email.uploading")} ${emailFiles.length}...`);

      try {
        const formData = new FormData();
        for (const f of emailFiles) formData.append("files", f);

        const res = await fetch("/api/emails/upload", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          setStatus(t("email.uploadFailed"));
          return;
        }

        const data = await res.json();
        if (data.files?.length) {
          setStatus(`+${data.files.length} ${t("email.uploadSuccess")}`);
          onFilesUploaded(data.files);
        } else {
          setStatus(t("email.uploadFailed"));
        }
      } catch {
        setStatus(t("email.uploadFailed"));
      } finally {
        setUploading(false);
        setTimeout(() => setStatus(""), 4000);
      }
    },
    [onFilesUploaded, t]
  );

  const handleBrowse = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".eml,.msg,.txt";
    input.multiple = true;
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
          <span className="text-primary font-medium animate-pulse">{status}</span>
        ) : isDragging ? (
          <span className="text-primary font-medium">{t("email.dropHere")}</span>
        ) : (
          <>
            <span className="text-muted-foreground">{t("email.dragFiles")}</span>
            <span className="text-muted-foreground/30">|</span>
            <button
              type="button"
              onClick={handleBrowse}
              className="text-primary hover:underline text-sm font-medium"
            >
              {t("email.browse")}
            </button>
          </>
        )}
      </div>

      {!uploading && status && (
        <p className={`mt-1 text-xs font-medium ${
          status.startsWith("+") ? "text-green-600" : "text-red-600"
        }`}>
          {status}
        </p>
      )}
    </div>
  );
}
