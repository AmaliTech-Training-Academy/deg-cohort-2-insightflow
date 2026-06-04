"use client";

import { useRef, useState } from "react";

interface FileDropzoneProps {
  onFile: (file: File) => void;
  accept?: string;
  disabled?: boolean;
}

export function FileDropzone({
  onFile,
  accept = ".csv,.xlsx",
  disabled = false,
}: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onFile(file);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) onFile(file);
  }

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => e.key === "Enter" && !disabled && inputRef.current?.click()}
      className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 text-sm transition-all select-none ${
        disabled
          ? "opacity-50 cursor-not-allowed border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50"
          : dragging
          ? "border-green-400 bg-green-50 dark:bg-green-950/40 cursor-copy scale-[1.01]"
          : "border-gray-300 dark:border-slate-600 bg-gray-50 dark:bg-slate-800/50 hover:border-green-400 dark:hover:border-green-500 hover:bg-green-50 dark:hover:bg-green-950/30 cursor-pointer"
      }`}
    >
      <span className={`mb-3 transition-colors ${dragging ? "text-green-500" : "text-gray-400 dark:text-slate-500"}`}>
        <UploadCloudIcon />
      </span>
      <p className="font-medium text-gray-700 dark:text-slate-300">
        {dragging ? "Release to upload" : "Drop a file here, or click to browse"}
      </p>
      <p className="text-gray-400 dark:text-slate-500 mt-1 text-xs">
        {accept.toUpperCase().replaceAll(",", " or ")}
      </p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={handleChange}
        disabled={disabled}
        tabIndex={-1}
      />
    </div>
  );
}

function UploadCloudIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 16 12 12 8 16" />
      <line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </svg>
  );
}
