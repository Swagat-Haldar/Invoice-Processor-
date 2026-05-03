"use client";

import React from "react";
import { FieldRenderer } from "./FieldRenderer";
import LineItemsTable from "./LineItemsTable";

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
  if (typeof value === "object" && value) {
    const entries = Object.entries(value as Record<string, unknown>);
    return entries.some(([, v]) => isRenderable(v));
  }
  return false;
}

type InvoiceViewProps = {
  invoice: any;
};

function Section({
  title,
  children,
  hidden,
}: {
  title: string;
  children: React.ReactNode;
  hidden?: boolean;
}) {
  if (hidden) return null;
  return (
    <section className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-2 text-sm font-semibold text-gray-900">
        {title}
      </div>
      <div className="px-4 py-3">{children}</div>
    </section>
  );
}

export default function InvoiceView({ invoice }: InvoiceViewProps) {
  if (!invoice || typeof invoice !== "object") return null;

  const invoiceMeta = invoice.invoice_meta;
  const seller = invoice.seller;
  const buyer = invoice.buyer;
  const totals = invoice.totals;
  const payment = invoice.payment;
  const notes = invoice.notes;
  const other = invoice.other;
  const lineItems = Array.isArray(invoice.line_items) ? invoice.line_items : [];

  const showLineItems = lineItems.length > 0;

  const headerHidden = ![invoiceMeta, seller, buyer].some((v) => isRenderable(v));
  const bodyHidden = ![totals].some((v) => isRenderable(v)) && !showLineItems;
  const footerHidden = ![payment, notes, other].some((v) => isRenderable(v));

  return (
    <div className="space-y-4">
      <Section title="Header" hidden={headerHidden}>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div>
            <div className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
              Invoice Meta
            </div>
            <FieldRenderer value={invoiceMeta} />
          </div>
          <div>
            <div className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
              Parties
            </div>
            <FieldRenderer value={{ seller, buyer }} />
          </div>
        </div>
      </Section>

      <Section title="Body" hidden={bodyHidden}>
        <div className="space-y-4">
          {showLineItems ? <LineItemsTable lineItems={lineItems} /> : null}
          {isRenderable(totals) ? (
            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
                Totals
              </div>
              <FieldRenderer value={totals} />
            </div>
          ) : null}
        </div>
      </Section>

      <Section title="Footer" hidden={footerHidden}>
        <div className="space-y-4">
          {isRenderable(payment) ? (
            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
                Payment
              </div>
              <FieldRenderer value={payment} />
            </div>
          ) : null}

          {isRenderable(notes) ? (
            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
                Notes
              </div>
              <div className="text-sm text-gray-900 whitespace-pre-wrap">{String(notes)}</div>
            </div>
          ) : null}

          {isRenderable(other) ? (
            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
                Other
              </div>
              <FieldRenderer value={other} />
            </div>
          ) : null}
        </div>
      </Section>
    </div>
  );
}

