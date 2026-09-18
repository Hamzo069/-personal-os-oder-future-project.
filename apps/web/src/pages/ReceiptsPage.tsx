import { CheckCircle2, Clock, FileWarning, RefreshCw, Trash2, UploadCloud } from "lucide-react";
import { useRef, useState, type ChangeEvent, type DragEvent } from "react";

import { useDeleteReceipt, useReceipts, useRetryExtraction, useUploadReceipt } from "@/api/hooks";
import { ReceiptReviewDialog } from "@/components/ReceiptReviewDialog";
import { Alert, Button, EmptyState, Spinner, cx } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatBytes, formatDate, formatMoney } from "@/lib/format";
import type { Receipt } from "@/types";

const ACCEPT = "image/jpeg,image/png,image/webp,application/pdf";

export function ReceiptsPage() {
  const { user } = useAuth();
  const receipts = useReceipts();
  const upload = useUploadReceipt();
  const retry = useRetryExtraction();
  const remove = useDeleteReceipt();
  const [reviewing, setReviewing] = useState<Receipt | null>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const onError = (err: unknown) => setError(err instanceof ApiError ? err.message : "Request failed");

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    setError(null);
    for (const file of Array.from(files)) upload.mutate(file, { onError });
  };

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    handleFiles(event.dataTransfer.files);
  };

  const pending = receipts.data?.filter((r) => r.status === "extracted") ?? [];
  const others = receipts.data?.filter((r) => r.status !== "extracted") ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Receipts</h1>
        <p className="text-sm text-slate-500">Upload a photo or PDF. The AI drafts the expense, you confirm it.</p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cx(
          "flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition",
          dragging ? "border-brand-500 bg-brand-50" : "border-slate-300 bg-white",
        )}
      >
        <UploadCloud className="h-8 w-8 text-brand-600" aria-hidden />
        <p className="mt-2 font-medium text-slate-800">Drag & drop receipts here</p>
        <p className="text-xs text-slate-500">JPEG, PNG, WebP or PDF · max 10 MB each</p>
        <Button className="mt-4" variant="secondary" onClick={() => inputRef.current?.click()} loading={upload.isPending}>
          Choose files
        </Button>
        <input ref={inputRef} type="file" accept={ACCEPT} multiple className="hidden" onChange={(e: ChangeEvent<HTMLInputElement>) => handleFiles(e.target.files)} />
      </div>

      {error && <Alert>{error}</Alert>}

      {receipts.isLoading ? (
        <Spinner />
      ) : !receipts.data?.length ? (
        <EmptyState title="No receipts yet" description="Your uploaded receipts and their extraction status will appear here." />
      ) : (
        <>
          {pending.length > 0 && (
            <section>
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-amber-700">Waiting for your review ({pending.length})</h2>
              <ul className="grid gap-3 sm:grid-cols-2">
                {pending.map((r) => (
                  <ReceiptCard key={r.id} receipt={r} currency={user?.default_currency ?? "EUR"} onReview={() => setReviewing(r)} onRetry={() => retry.mutate(r.id, { onError })} onDelete={() => remove.mutate(r.id, { onError })} />
                ))}
              </ul>
            </section>
          )}
          {others.length > 0 && (
            <section>
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">All receipts</h2>
              <ul className="grid gap-3 sm:grid-cols-2">
                {others.map((r) => (
                  <ReceiptCard key={r.id} receipt={r} currency={user?.default_currency ?? "EUR"} onReview={() => setReviewing(r)} onRetry={() => retry.mutate(r.id, { onError })} onDelete={() => remove.mutate(r.id, { onError })} />
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      <ReceiptReviewDialog receipt={reviewing} currency={user?.default_currency ?? "EUR"} onClose={() => setReviewing(null)} />
    </div>
  );
}

const STATUS: Record<Receipt["status"], { label: string; icon: typeof Clock; className: string }> = {
  uploaded: { label: "Queued", icon: Clock, className: "text-slate-500" },
  processing: { label: "Extracting…", icon: RefreshCw, className: "text-brand-600" },
  extracted: { label: "Needs review", icon: Clock, className: "text-amber-700" },
  confirmed: { label: "Booked", icon: CheckCircle2, className: "text-green-700" },
  failed: { label: "Failed", icon: FileWarning, className: "text-red-700" },
};

function ReceiptCard({
  receipt,
  currency,
  onReview,
  onRetry,
  onDelete,
}: {
  receipt: Receipt;
  currency: string;
  onReview: () => void;
  onRetry: () => void;
  onDelete: () => void;
}) {
  const status = STATUS[receipt.status];
  const Icon = status.icon;
  const x = receipt.extracted;
  return (
    <li className="flex flex-col justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className="truncate font-medium text-slate-900" title={receipt.original_filename}>
            {x?.merchant ?? receipt.original_filename}
          </p>
          <span className={cx("flex shrink-0 items-center gap-1 text-xs font-medium", status.className)}>
            <Icon className={cx("h-3.5 w-3.5", receipt.status === "processing" && "animate-spin")} aria-hidden />
            {status.label}
          </span>
        </div>
        <p className="text-xs text-slate-500">
          {formatDate(receipt.created_at)} · {formatBytes(receipt.size_bytes)}
          {x?.total_amount != null && <> · {formatMoney(x.total_amount, x.currency ?? currency)}</>}
          {x?.category && <> · {x.category}</>}
        </p>
        {receipt.error_message && <p className="mt-1 text-xs text-red-600">{receipt.error_message}</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        {receipt.status === "extracted" && (
          <Button size="sm" onClick={onReview}>
            Review & book
          </Button>
        )}
        {receipt.status === "failed" && (
          <>
            <Button size="sm" variant="secondary" onClick={onRetry}>
              <RefreshCw className="h-3.5 w-3.5" aria-hidden /> Retry
            </Button>
            <Button size="sm" variant="secondary" onClick={onReview}>
              Enter manually
            </Button>
          </>
        )}
        {receipt.status === "confirmed" && (
          <Button size="sm" variant="ghost" onClick={onReview}>
            View
          </Button>
        )}
        <Button size="sm" variant="ghost" className="ml-auto text-slate-500" onClick={() => window.confirm("Delete this receipt file?") && onDelete()} aria-label="Delete receipt">
          <Trash2 className="h-3.5 w-3.5" aria-hidden />
        </Button>
      </div>
    </li>
  );
}
