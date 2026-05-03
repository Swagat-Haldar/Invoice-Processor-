"use client";

import React, { useMemo } from "react";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";

type LineItem = Record<string, unknown>;

export type LineItemsTableProps = {
  lineItems: LineItem[];
};

function firstNonEmptyValue(item: LineItem, keys: string[]) {
  for (const k of keys) {
    const v = item[k];
    if (v === null || v === undefined) continue;
    if (typeof v === "string") {
      const s = v.trim();
      if (s.length > 0) return v;
      continue;
    }
    if (typeof v === "number") return v;
    if (Array.isArray(v) && v.length > 0) return v;
    if (typeof v === "boolean") return v;
  }
  return undefined as unknown;
}

function parseNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "object") {
    // Some invoices/models return tax as an object of components (cgst/sgst/igst).
    const obj = value as Record<string, unknown>;
    let sum = 0;
    let hasAny = false;
    for (const v of Object.values(obj)) {
      const n = parseNumber(v);
      if (n === null) continue;
      sum += n;
      hasAny = true;
    }
    return hasAny ? sum : null;
  }
  if (typeof value !== "string") return null;
  const s = value.replace(/,/g, "").trim();
  const cleaned = s.replace(/[^0-9.\-]/g, "");
  if (!cleaned || cleaned === "-" || cleaned === ".") return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

function formatNumber(n: number, decimals: number = 3) {
  if (!Number.isFinite(n)) return "";
  const fixed = n.toFixed(decimals);
  // Trim trailing zeros while preserving at least one decimal if the input is decimal.
  return fixed.replace(/\.?0+$/, (m) => (m.startsWith(".") ? "" : m));
}

function normalizeToArray(v: unknown): unknown[] {
  if (Array.isArray(v)) return v;
  if (v === null || v === undefined) return [];
  return [v];
}

function toArrayWithTarget(v: unknown, targetLen: number): unknown[] {
  if (Array.isArray(v)) return v;
  if (v === null || v === undefined) return [];
  if (typeof v === "string") {
    const s = v.trim();
    if (!s) return [];
    if (targetLen > 1 && (s.includes(",") || s.includes("\n") || s.includes(";") || s.includes("|"))) {
      const parts = s
        .split(/[\n,;|]+/g)
        .map((x) => x.trim())
        .filter((x) => x.length > 0);
      // Only accept the split if it looks like it provides multiple values.
      if (parts.length >= 2) return parts;
    }
    return [s];
  }
  return [v];
}

type NormalizedRow = {
  id: string;
  sr_no?: string;
  item_code?: string;
  description: string;
  quantity?: string;
  unit_price?: string;
  tax?: string;
  // For totals calculations
  _quantity_num: number | null;
  _unit_price_num: number | null;
  _tax_num: number | null;
};

export default function LineItemsTable({ lineItems }: LineItemsTableProps) {
  const rows = useMemo(() => {
    const out: NormalizedRow[] = [];
    const items = Array.isArray(lineItems) ? lineItems : [];

    for (let idx = 0; idx < items.length; idx++) {
      const it = items[idx] ?? {};

      const descRaw = firstNonEmptyValue(it, ["description", "item", "name", "product"]);
      const srRaw = firstNonEmptyValue(it, ["sr_no", "srNo", "sr no", "sr_no_"]);
      const itemCodeRaw = firstNonEmptyValue(it, [
        "item_code",
        "itemCode",
        "item code",
        "code",
        "itemcode",
        "sku",
      ]);

      const qtyRaw = firstNonEmptyValue(it, ["quantity", "qty"]);
      const unitRaw = firstNonEmptyValue(it, [
        "unit_price",
        "unitPrice",
        "unit cost",
        "unit_amount",
        "unitAmount",
        "rate",
      ]);

      // Tax can show up under multiple key names. We compute a numeric tax per row by summing
      // any numeric-like tax component at the same index.
      const taxComponentKeys = [
        "tax",
        "tax_amount",
        "taxAmount",
        "gst",
        "gst_amount",
        "gstAmount",
        "igst",
        "igst_amount",
        "igstAmount",
        "cgst",
        "cgst_amount",
        "cgstAmount",
        "sgst",
        "sgst_amount",
        "sgstAmount",
        "vat",
      ];
      const taxComponents: unknown[] = [];
      for (const k of taxComponentKeys) {
        const v = it[k];
        if (v !== null && v !== undefined && v !== "") taxComponents.push(v);
      }

      // Determine the "row count" by looking at array lengths for quantity/unit/tax/components.
      const lens: number[] = [];
      const maybeLens = [descRaw, srRaw, itemCodeRaw, qtyRaw, unitRaw, ...taxComponents];
      for (const v of maybeLens) {
        if (Array.isArray(v)) lens.push(v.length);
      }
      const targetLen = Math.max(...lens, 1);

      const descArr = toArrayWithTarget(descRaw, targetLen);
      const srArr = toArrayWithTarget(srRaw, targetLen);
      const itemCodeArr = toArrayWithTarget(itemCodeRaw, targetLen);
      const qtyArr = toArrayWithTarget(qtyRaw, targetLen);
      const unitArr = toArrayWithTarget(unitRaw, targetLen);
      const taxArrs = taxComponents.map((v) => toArrayWithTarget(v, targetLen));

      for (let i = 0; i < targetLen; i++) {
        const description = String(descArr[i] ?? descArr[0] ?? "").trim();
        const srNoStr = String(srArr[i] ?? srArr[0] ?? "").trim();
        const itemCodeStr = String(itemCodeArr[i] ?? itemCodeArr[0] ?? "").trim();
        const quantityStr = String(qtyArr[i] ?? qtyArr[0] ?? "").trim();
        const unitStr = String(unitArr[i] ?? unitArr[0] ?? "").trim();

        let taxNumSum: number | null = 0;
        for (const arr of taxArrs) {
          const maybe = arr[i] ?? arr[0];
          const n = parseNumber(maybe);
          if (n === null) continue;
          taxNumSum = (taxNumSum ?? 0) + n;
        }
        const taxStr = taxNumSum === null || taxNumSum === 0 ? "" : String(taxNumSum);

        const row: NormalizedRow = {
          id: `${idx}-${i}`,
          sr_no: srNoStr.length ? srNoStr : undefined,
          item_code: itemCodeStr.length ? itemCodeStr : undefined,
          description,
          quantity: quantityStr.length ? quantityStr : undefined,
          unit_price: unitStr.length ? unitStr : undefined,
          tax: taxStr.length ? taxStr : undefined,
          _quantity_num: parseNumber(quantityStr),
          _unit_price_num: parseNumber(unitStr),
          _tax_num: parseNumber(taxStr),
        };

        out.push(row);
      }
    }

    // Avoid rendering rows that have no meaningful description/value.
    return out.filter((r) => {
      return (
        r.description.trim().length > 0 ||
        (r.item_code ? r.item_code.trim().length > 0 : false) ||
        !!r.quantity ||
        !!r.unit_price ||
        !!r.tax
      );
    });
  }, [lineItems]);

  const totals = useMemo(() => {
    let qtySum = 0;
    let productSum = 0;
    let taxSum = 0;

    let hasQty = false;
    let hasProduct = false;
    let hasTax = false;

    for (const r of rows) {
      if (r._quantity_num !== null) {
        qtySum += r._quantity_num;
        hasQty = true;
      }
      if (r._quantity_num !== null && r._unit_price_num !== null) {
        productSum += r._quantity_num * r._unit_price_num;
        hasProduct = true;
      }
      if (r._tax_num !== null) {
        taxSum += r._tax_num;
        hasTax = true;
      }
    }

    const grandTotal = hasProduct && hasTax ? productSum + taxSum : null;

    return {
      hasQty,
      qtySum: hasQty ? qtySum : null,
      hasProduct,
      productSum: hasProduct ? productSum : null,
      hasTax,
      taxSum: hasTax ? taxSum : null,
      grandTotal,
    };
  }, [rows]);

  const columns = useMemo<ColumnDef<NormalizedRow>[]>(
    () => {
      const anySr = rows.some((r) => (r.sr_no ?? "").trim().length > 0);
      const anyItemCode = rows.some((r) => (r.item_code ?? "").trim().length > 0);
      const anyQuantity = rows.some((r) => (r.quantity ?? "").trim().length > 0);
      const anyUnit = rows.some((r) => (r.unit_price ?? "").trim().length > 0);
      const anyTax = rows.some((r) => (r.tax ?? "").trim().length > 0);

      const cols: ColumnDef<NormalizedRow>[] = [];

      if (anySr) {
        cols.push({
          header: "Sr No",
          accessorKey: "sr_no",
          cell: (info) => (
            <span className="break-words whitespace-normal">{info.getValue<string>()}</span>
          ),
        });
      }

      if (anyItemCode) {
        cols.push({
          header: "Item Code",
          accessorKey: "item_code",
          cell: (info) => (
            <span className="break-words whitespace-normal">{info.getValue<string>()}</span>
          ),
        });
      }

      cols.push({
        header: "Description",
        accessorKey: "description",
        cell: (info) => (
          <span className="break-words whitespace-normal">{info.getValue<string>()}</span>
        ),
      });

      if (anyQuantity) {
        cols.push({
          header: "Quantity",
          accessorKey: "quantity",
          cell: (info) => (
            <span className="break-words whitespace-normal">{info.getValue<string>()}</span>
          ),
        });
      }

      if (anyUnit) {
        cols.push({
          header: "Unit Price",
          accessorKey: "unit_price",
          cell: (info) => (
            <span className="break-words whitespace-normal">{info.getValue<string>()}</span>
          ),
        });
      }

      if (anyTax) {
        cols.push({
          header: "Tax",
          accessorKey: "tax",
          cell: (info) => (
            <span className="break-words whitespace-normal">{info.getValue<string>()}</span>
          ),
        });
      }

      return cols;
    },
    [rows]
  );

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (!rows.length) return null;

  return (
    <section className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-2 text-sm font-semibold text-gray-900">
        Line Items
      </div>
      <div className="overflow-auto">
        <table className="min-w-full table-fixed border-collapse">
          <thead className="bg-gray-50">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className="border-b border-gray-200 px-4 py-2 text-left text-xs font-medium text-gray-600"
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="hover:bg-gray-50">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="border-b border-gray-200 px-4 py-2 text-sm text-gray-900">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {(totals.hasQty || totals.hasProduct || totals.hasTax || totals.grandTotal !== null) ? (
        <div className="mt-4 rounded-lg border border-gray-200 bg-white">
          <div className="border-b border-gray-200 px-4 py-2 text-sm font-semibold text-gray-900">
            Invoice Totals
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 px-4 py-3 text-sm">
            {totals.hasQty ? (
              <>
                <div className="text-gray-600">Quantity</div>
                <div className="font-medium text-gray-900">{formatNumber(totals.qtySum!, 0)}</div>
              </>
            ) : null}
            {totals.hasProduct ? (
              <>
                <div className="text-gray-600">Total Product Amount</div>
                <div className="font-medium text-gray-900">{formatNumber(totals.productSum!, 3)}</div>
              </>
            ) : null}
            {totals.hasTax ? (
              <>
                <div className="text-gray-600">Tax</div>
                <div className="font-medium text-gray-900">{formatNumber(totals.taxSum!, 3)}</div>
              </>
            ) : null}
            {totals.grandTotal !== null ? (
              <>
                <div className="text-gray-600">Grand Total</div>
                <div className="font-medium text-gray-900">{formatNumber(totals.grandTotal!, 3)}</div>
              </>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}

