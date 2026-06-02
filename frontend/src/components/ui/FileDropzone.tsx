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
      tabIndex={0}
      aria-disabled={disabled}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => e.key === "Enter" && !disabled && inputRef.current?.click()}
      className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 text-sm transition-colors cursor-pointer ${
        dragging
          ? "border-blue-400 bg-blue-50"
          : "border-gray-300 bg-gray-50 hover:border-gray-400"
      } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <span className="text-3xl mb-3">📁</span>
      <p className="font-medium text-gray-700">Drop a file here or click to browse</p>
      <p className="text-gray-500 mt-1">Accepts {accept}</p>
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
