"use client";

import { useState } from "react";

import AppFooter from "../components/AppFooter";
import AppHeader from "../components/AppHeader";
import InvoiceView from "../components/InvoiceView";
import JsonViewer from "../components/JsonViewer";
import UploadSection from "../components/UploadSection";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function Page() {
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | undefined>(undefined);
  const [rawJson, setRawJson] = useState<any | null>(null);

  async function onUpload(file: File) {
    setIsUploading(true);
    setErrorMessage(undefined);
    setRawJson(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const resp = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      const contentType = resp.headers.get("content-type") || "";
      const json = contentType.includes("application/json") ? await resp.json() : null;
      if (!resp.ok) {
        const msg = json?.message || `Request failed with status ${resp.status}`;
        setErrorMessage(msg);
        return;
      }

      setRawJson(json);
    } catch (e: any) {
      setErrorMessage(e?.message ? String(e.message) : "Network error while uploading.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <AppHeader />

      <main className="mx-auto max-w-5xl px-4 py-6">
        <div className="space-y-4">
          <UploadSection
            onUpload={onUpload}
            isUploading={isUploading}
            errorMessage={errorMessage}
          />

          {rawJson ? (
            <div className="space-y-4">
              <InvoiceView invoice={rawJson} />
              <JsonViewer json={rawJson} title="Raw JSON" />
            </div>
          ) : null}
        </div>
      </main>

      <AppFooter />
    </div>
  );
}

