"use client";

import { useMemo } from "react";
import type { Comparable, Subject } from "@/lib/types";
import { money } from "@/lib/format";

// Dependency-free proximity plot: subject at the center, comparables placed by
// their coordinates, with distance rings in miles. Deliberately not a tile
// map (no external servers, no licensing, works offline) while still
// answering the question a map answers during comp selection: "how far, and
// in which direction?" The comparables table remains the accessible source
// of the same data.

const MILES_PER_DEG_LAT = 69.05;

interface Point {
  comp: Comparable;
  x: number; // miles east of subject
  y: number; // miles north of subject
  included: boolean;
  similarity: number | null;
}

function project(subject: Subject, comp: Comparable): { x: number; y: number } | null {
  if (
    subject.latitude == null || subject.longitude == null ||
    comp.latitude == null || comp.longitude == null
  )
    return null;
  const milesPerDegLon =
    MILES_PER_DEG_LAT * Math.cos((subject.latitude * Math.PI) / 180);
  return {
    x: (comp.longitude - subject.longitude) * milesPerDegLon,
    y: (comp.latitude - subject.latitude) * MILES_PER_DEG_LAT,
  };
}

function ringStep(maxMiles: number): number {
  if (maxMiles <= 1.5) return 0.5;
  if (maxMiles <= 3) return 1;
  if (maxMiles <= 8) return 2;
  return 5;
}

export function CompMap({
  subject,
  comparables,
}: {
  subject: Subject;
  comparables: Comparable[];
}) {
  const { points, unplotted } = useMemo(() => {
    const pts: Point[] = [];
    let missing = 0;
    for (const comp of comparables) {
      const pos = project(subject, comp);
      if (pos === null) {
        missing += 1;
        continue;
      }
      pts.push({
        comp,
        ...pos,
        included: comp.selection?.included !== false,
        similarity: comp.selection?.similarity_score ?? null,
      });
    }
    return { points: pts, unplotted: missing };
  }, [subject, comparables]);

  if (subject.latitude == null || subject.longitude == null) {
    return (
      <p className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
        Add latitude/longitude to the subject property to see the proximity map.
      </p>
    );
  }
  if (points.length === 0) {
    return (
      <p className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
        No comparables have coordinates yet. The proximity map will appear once
        they do.
      </p>
    );
  }

  const maxDist = Math.max(...points.map((p) => Math.hypot(p.x, p.y)), 0.5);
  const step = ringStep(maxDist);
  const rings: number[] = [];
  for (let r = step; r <= maxDist + step * 0.999; r += step) rings.push(r);
  const extent = rings[rings.length - 1];

  // viewBox is in miles, y flipped so north is up.
  const pad = extent * 0.12;
  const size = (extent + pad) * 2;
  const view = `${-(extent + pad)} ${-(extent + pad)} ${size} ${size}`;
  const dot = extent / 22;

  return (
    <figure>
      <div className="mx-auto max-w-md">
        <svg
          viewBox={view}
          role="img"
          aria-label={`Proximity map: ${points.length} comparable(s) plotted around the subject; rings every ${step} mile(s). The comparables table lists the same distances.`}
          className="w-full"
        >
          {rings.map((r) => (
            <g key={r}>
              <circle
                cx={0}
                cy={0}
                r={r}
                fill="none"
                stroke="#cbd5e1"
                strokeWidth={extent / 220}
                strokeDasharray={`${extent / 60} ${extent / 60}`}
              />
              <text
                x={0}
                y={-r}
                dy={extent * 0.045}
                textAnchor="middle"
                fontSize={extent * 0.055}
                fill="#94a3b8"
              >
                {r % 1 === 0 ? r : r.toFixed(1)} mi
              </text>
            </g>
          ))}

          {points.map((p) => (
            <circle
              key={p.comp.id}
              cx={p.x}
              cy={-p.y}
              r={p.included ? dot : dot * 0.75}
              fill={p.included ? "#1d4ed8" : "#94a3b8"}
              fillOpacity={
                p.included
                  ? 0.35 + 0.65 * ((p.similarity ?? 60) / 100)
                  : 0.35
              }
              stroke={p.included ? "#1e40af" : "#64748b"}
              strokeWidth={extent / 300}
            >
              <title>
                {`${p.comp.address}: ${money(p.comp.sale_price)}, ` +
                  `${Math.hypot(p.x, p.y).toFixed(2)} mi` +
                  (p.similarity !== null
                    ? `, similarity ${p.similarity.toFixed(0)}`
                    : "") +
                  (p.included ? "" : " (excluded)")}
              </title>
            </circle>
          ))}

          {/* Subject marker: house-ish diamond at the center */}
          <g>
            <rect
              x={-dot * 1.1}
              y={-dot * 1.1}
              width={dot * 2.2}
              height={dot * 2.2}
              transform="rotate(45)"
              fill="#0f172a"
              stroke="#ffffff"
              strokeWidth={extent / 200}
            />
            <title>{`Subject: ${subject.address}`}</title>
          </g>
        </svg>
      </div>
      <figcaption className="mt-1 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block h-2.5 w-2.5 rotate-45 bg-slate-900" />
          Subject
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block h-2.5 w-2.5 rounded-full bg-accent-700" />
          Included (darker = more similar)
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block h-2.5 w-2.5 rounded-full bg-slate-400 opacity-60" />
          Excluded
        </span>
        {unplotted > 0 && (
          <span>{unplotted} comparable(s) without coordinates not plotted.</span>
        )}
      </figcaption>
    </figure>
  );
}
