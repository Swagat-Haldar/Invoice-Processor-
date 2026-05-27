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
    <section className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
      <div className="border-b border-gray-200 px-4 py-2 text-sm font-semibold text-gray-900 dark:border-gray-700 dark:text-gray-100">
        {title}
      </div>
      <pre className="max-h-[420px] overflow-auto px-4 py-3 text-xs text-gray-800 dark:text-gray-200">
        {pretty}
      </pre>
    </section>
  );
}

