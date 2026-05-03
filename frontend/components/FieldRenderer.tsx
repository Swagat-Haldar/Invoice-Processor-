"use client";

import React from "react";

function isRenderablePrimitive(value: unknown) {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value === "boolean") return true;
  return false;
}

function isRenderable(value: unknown): boolean {
  if (isRenderablePrimitive(value)) return true;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") {
    if (!value) return false;
    const entries = Object.entries(value as Record<string, unknown>);
    return entries.some(([, v]) => isRenderable(v));
  }
  return false;
}

function renderScalar(value: unknown) {
  if (value === null || value === undefined) return null;
  return <span className="whitespace-pre-wrap break-words">{String(value)}</span>;
}

export type FieldRendererProps = {
  value: unknown;
  depth?: number;
};

export function FieldRenderer({ value, depth = 0 }: FieldRendererProps) {
  if (!isRenderable(value)) return null;

  if (isRenderablePrimitive(value)) {
    return <div className="text-sm text-gray-900">{renderScalar(value)}</div>;
  }

  if (Array.isArray(value)) {
    // Keep arrays readable while avoiding hardcoded invoice assumptions.
    if (value.length === 0) return null;
    return (
      <ul className="list-disc pl-5 text-sm text-gray-900">
        {value
          .filter((v) => isRenderable(v))
          .slice(0, 50)
          .map((v, idx) => (
            <li key={idx}>
              <FieldRenderer value={v} depth={depth + 1} />
            </li>
          ))}
      </ul>
    );
  }

  if (typeof value === "object" && value) {
    const obj = value as Record<string, unknown>;
    const entries = Object.entries(obj).filter(([, v]) => isRenderable(v));

    if (entries.length === 0) return null;

    // Depth-based layout: shallow objects get table-like rows.
    if (depth <= 1) {
      return (
        <div className="grid grid-cols-1 gap-y-2">
          {entries.map(([k, v]) => (
            <div key={k}>
              <div className="text-xs font-medium uppercase tracking-wide text-gray-500">{k}</div>
              <FieldRenderer value={v} depth={depth + 1} />
            </div>
          ))}
        </div>
      );
    }

    // Deeper nested structures: still render but with indentation.
    return (
      <div className="ml-3">
        {entries.map(([k, v]) => (
          <div key={k} className="mb-2">
            <div className="text-xs font-medium uppercase tracking-wide text-gray-500">{k}</div>
            <FieldRenderer value={v} depth={depth + 1} />
          </div>
        ))}
      </div>
    );
  }

  return null;
}

