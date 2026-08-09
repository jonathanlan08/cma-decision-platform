"use client";

import { useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { CSVImportResult } from "@/lib/types";
import { ErrorBox } from "./ui";

export function CsvUpload({
  cmaId,
  onImported,
}: {
  cmaId: number;
  onImported: (result: CSVImportResult) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CSVImportResult | null>(null);

  async function handleUpload(file: File) {
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const imported = await api.importCsv(cmaId, file);
      setResult(imported);
      onImported(imported);
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <label htmlFor="csv-file" className="btn-secondary cursor-pointer">
          {uploading ? "Uploading…" : "Upload CSV of sold comparables"}
          <input
            ref={inputRef}
            id="csv-file"
            type="file"
            accept=".csv,text/csv"
            className="sr-only"
            disabled={uploading}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleUpload(file);
            }}
          />
        </label>
        <a
          href={api.csvTemplateUrl()}
          className="text-sm text-accent-700 underline-offset-2 hover:underline"
          download
        >
          Download CSV template
        </a>
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Use your own exported data or the bundled synthetic sample
        (<code>data/sample/comparables_sample.csv</code>). Do not upload confidential MLS
        exports you are not licensed to use.
      </p>

      {error && <ErrorBox message={error} />}

      {result && (
        <div
          role="status"
          className={`mt-3 rounded-md border px-3 py-2 text-sm ${
            result.error_count > 0
              ? "border-amber-300 bg-amber-50 text-amber-900"
              : "border-emerald-300 bg-emerald-50 text-emerald-900"
          }`}
        >
          Imported {result.imported_count} comparable(s).
          {result.error_count > 0 && <> {result.error_count} row(s) had errors:</>}
          {result.error_count > 0 && (
            <div className="mt-2 overflow-x-auto">
              <table className="data-table bg-white">
                <caption className="sr-only">Row-level validation errors</caption>
                <thead>
                  <tr>
                    <th scope="col">Row</th>
                    <th scope="col">Field</th>
                    <th scope="col">Problem</th>
                  </tr>
                </thead>
                <tbody>
                  {result.errors.map((err, i) => (
                    <tr key={i}>
                      <td className="num">{err.row}</td>
                      <td>{err.field}</td>
                      <td>{err.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
