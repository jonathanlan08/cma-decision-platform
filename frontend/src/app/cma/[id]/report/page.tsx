"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Report } from "@/lib/types";
import { Card, EmptyState, ErrorBox, Spinner } from "@/components/ui";
import { dateTime } from "@/lib/format";
import { useCma } from "../cma-context";

export default function ReportPage() {
  const { cma } = useCma();
  const [reports, setReports] = useState<Report[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  const load = useCallback(() => {
    setError(null);
    api
      .listReports(cma.id)
      .then(setReports)
      .catch((e: ApiError) => setError(e.message));
  }, [cma.id]);

  useEffect(load, [load]);

  async function generate() {
    setGenerating(true);
    setError(null);
    try {
      const report = await api.generateReport(cma.id);
      load();
      window.open(api.reportDownloadUrl(report.id), "_blank", "noopener");
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <Card
      title="Seller-facing CMA report"
      actions={
        <button
          type="button"
          className="btn-primary"
          onClick={generate}
          disabled={generating || !cma.subject}
        >
          {generating ? "Generating…" : "Generate report"}
        </button>
      }
    >
      <p className="mb-3 text-sm text-slate-500">
        Produces a print-ready report: subject summary, methodology, comparable sales,
        the full adjustment grid, value reconciliation, strategy comparison, assumptions,
        and the limitations disclaimer. When server-side PDF conversion (WeasyPrint) is
        installed the download is a PDF; otherwise it opens as print-optimized HTML — use
        your browser&apos;s “Print → Save as PDF”.
      </p>
      {!cma.subject && (
        <p className="text-sm text-amber-800">Enter the subject property first.</p>
      )}
      {error && <ErrorBox message={error} onRetry={load} />}
      {!reports && !error && <Spinner label="Loading reports…" />}
      {reports && reports.length === 0 && (
        <EmptyState title="No reports generated yet">
          <p>Each generated report is kept with its calculation version for the audit trail.</p>
        </EmptyState>
      )}
      {reports && reports.length > 0 && (
        <div className="overflow-x-auto">
          <table className="data-table">
            <caption>Generated reports (newest last)</caption>
            <thead>
              <tr>
                <th scope="col">Generated</th>
                <th scope="col">Format</th>
                <th scope="col">Methodology</th>
                <th scope="col"><span className="sr-only">Download</span></th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.id}>
                  <td>{dateTime(report.created_at)}</td>
                  <td className="uppercase">{report.format}</td>
                  <td>{report.calc_version}</td>
                  <td>
                    <a
                      href={api.reportDownloadUrl(report.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent-700 underline-offset-2 hover:underline"
                    >
                      Open report<span className="sr-only"> generated {dateTime(report.created_at)}</span>
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
