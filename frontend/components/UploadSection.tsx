"use client";

import { useMemo, useState } from "react";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".jpg", ".jpeg", ".png", ".txt"];

export type UploadSectionProps = {
  onUpload: (file: File) => Promise<void>;
  isUploading: boolean;
  errorMessage?: string;
};

export default function UploadSection({
  onUpload,
  isUploading,
  errorMessage,
}: UploadSectionProps) {
  const [file, setFile] = useState<File | null>(null);
  const acceptAttr = useMemo(() => ACCEPTED_EXTENSIONS.join(","), []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    await onUpload(file);
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">Upload invoice</h2>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Supports PDF, DOCX, JPG, PNG, TXT. Gemini processes pages without OCR.
          </p>
        </div>
        {isUploading ? (
          <div className="text-sm text-gray-600 dark:text-gray-400">Processing…</div>
        ) : (
          <div className="text-sm text-gray-600 dark:text-gray-400">Ready</div>
        )}
      </div>

      <div className="mt-4">
        <input
          type="file"
          accept={acceptAttr}
          onChange={(e) => {
            const f = e.target.files?.[0] ?? null;
            setFile(f);
          }}
          className="block w-full text-sm text-gray-700 file:mr-4 file:rounded-md file:border-0 file:bg-indigo-50 file:px-3 file:py-2 file:text-indigo-700 hover:file:bg-indigo-100 dark:text-gray-300 dark:file:bg-indigo-900/30 dark:file:text-indigo-300 dark:hover:file:bg-indigo-900/50"
        />
      </div>

      {file ? (
        <div className="mt-2 text-sm text-gray-700 dark:text-gray-300">
          Selected: <span className="font-medium dark:text-gray-200">{file.name}</span>
        </div>
      ) : null}

      {errorMessage ? <div className="mt-3 text-sm text-red-600 dark:text-red-400">{errorMessage}</div> : null}

      <button
        type="submit"
        disabled={!file || isUploading}
        className="mt-4 inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        Upload & Extract
      </button>
    </form>
  );
}

