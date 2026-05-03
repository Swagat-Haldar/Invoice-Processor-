"use client";

import { useMemo } from "react";

export type JsonViewerProps = {
  json: unknown;
  title?: string;
};

export default function JsonViewer({ json, title = "Raw JSON" }: JsonViewerProps) {
  const pretty = useMemo(() => {
    try {
      return JSON.stringify(json, null, 2);
    } catch {
      return String(json);
    }
  }, [json]);

  return (
    <section className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-2 text-sm font-semibold text-gray-900">
        {title}
      </div>
      <pre className="max-h-[420px] overflow-auto px-4 py-3 text-xs text-gray-800">
        {pretty}
      </pre>
    </section>
  );
}

