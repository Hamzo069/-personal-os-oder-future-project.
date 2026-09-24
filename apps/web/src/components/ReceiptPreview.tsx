/**
 * Loads the receipt file with the Bearer token (an <img src> cannot send it)
 * and shows it as an object URL. PDFs are embedded in an iframe.
 */

import { useEffect, useState } from "react";

import { apiUrl, getAccessToken } from "@/lib/api";
import type { Receipt } from "@/types";

export function ReceiptPreview({ receipt }: { receipt: Receipt }) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(apiUrl(`/receipts/${receipt.id}/file`), {
          headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
          credentials: "include",
        });
        if (!response.ok) throw new Error("failed");
        objectUrl = URL.createObjectURL(await response.blob());
        if (!cancelled) setUrl(objectUrl);
      } catch {
        if (!cancelled) setError(true);
      }
    })();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [receipt.id]);

  if (error) return <p className="text-sm text-red-600">Preview unavailable.</p>;
  if (!url) return <div className="h-64 animate-pulse rounded-lg bg-slate-100" aria-hidden />;
  if (receipt.media_type === "application/pdf") {
    return <iframe src={url} title={receipt.original_filename} className="h-96 w-full rounded-lg border border-slate-200" />;
  }
  return (
    <img
      src={url}
      alt={`Receipt ${receipt.original_filename}`}
      className="max-h-96 w-full rounded-lg border border-slate-200 object-contain"
    />
  );
}
