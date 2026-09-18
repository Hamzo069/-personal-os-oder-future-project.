/**
 * Review an AI-extracted receipt: the file preview sits next to the editable
 * draft. Nothing is booked until the user confirms - the human stays in the loop.
 */

import { AlertTriangle } from "lucide-react";

import { useCategories, useConfirmReceipt } from "@/api/hooks";
import { TransactionForm, emptyValues, type TransactionFormValues } from "@/components/TransactionForm";
import { Alert, Dialog, Spinner } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { todayIso } from "@/lib/format";
import { ReceiptPreview } from "@/components/ReceiptPreview";
import type { Receipt } from "@/types";

export function draftFromReceipt(receipt: Receipt, currency: string): TransactionFormValues {
  const x = receipt.extracted;
  const base = emptyValues(currency);
  if (!x) return base;
  return {
    ...base,
    date: x.date ?? todayIso(),
    merchant: x.merchant ?? "",
    amount: x.total_amount != null ? x.total_amount.toFixed(2) : "",
    currency: x.currency ?? currency,
    vat_rate: x.vat_rate != null ? String(x.vat_rate) : "",
    vat_amount: x.vat_amount != null ? x.vat_amount.toFixed(2) : "",
    category_id: receipt.suggested_category_id ?? "",
    description: x.description ?? "",
    notes: "",
  };
}

export function ReceiptReviewDialog({
  receipt,
  currency,
  onClose,
}: {
  receipt: Receipt | null;
  currency: string;
  onClose: () => void;
}) {
  const categories = useCategories();
  const confirm = useConfirmReceipt();

  return (
    <Dialog open={receipt !== null} title={receipt?.status === "confirmed" ? "Receipt" : "Review receipt"} onClose={onClose} wide>
      {receipt && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
          <div className="space-y-3">
            <ReceiptPreview receipt={receipt} />
            {receipt.extracted?.notes && (
              <p className="flex items-start gap-2 text-xs text-slate-600">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" aria-hidden />
                {receipt.extracted.notes}
              </p>
            )}
            {receipt.confidence != null && (
              <p className="text-xs text-slate-500">AI confidence: {(receipt.confidence * 100).toFixed(0)} %</p>
            )}
            {receipt.extracted?.line_items?.length ? (
              <details className="text-xs text-slate-600">
                <summary className="cursor-pointer font-medium">Line items ({receipt.extracted.line_items.length})</summary>
                <ul className="mt-1 space-y-0.5">
                  {receipt.extracted.line_items.map((item, i) => (
                    <li key={i} className="flex justify-between gap-2">
                      <span className="truncate">{item.description}</span>
                      <span className="tabular-nums">{item.total != null ? item.total.toFixed(2) : ""}</span>
                    </li>
                  ))}
                </ul>
              </details>
            ) : null}
          </div>
          <div>
            {confirm.isError && (
              <div className="mb-3">
                <Alert>{confirm.error instanceof ApiError ? confirm.error.message : "Could not save"}</Alert>
              </div>
            )}
            {receipt.status === "confirmed" ? (
              <Alert kind="success">This receipt is already booked as an expense. Edit it on the Transactions page.</Alert>
            ) : categories.isLoading ? (
              <Spinner />
            ) : (
              <TransactionForm
                key={receipt.id}
                initial={draftFromReceipt(receipt, currency)}
                categories={categories.data ?? []}
                submitLabel="Confirm & book"
                loading={confirm.isPending}
                onCancel={onClose}
                onSubmit={(input) => confirm.mutate({ id: receipt.id, ...input }, { onSuccess: onClose })}
              />
            )}
          </div>
        </div>
      )}
    </Dialog>
  );
}

