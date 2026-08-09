"use client";

import { useState } from "react";
import type { Subject } from "@/lib/types";
import { Field } from "./ui";

const PROPERTY_TYPES = [
  "single_family",
  "condo",
  "townhouse",
  "multi_family",
  "manufactured",
  "other",
];
const CONDITIONS = ["poor", "fair", "average", "good", "excellent"];

export type SubjectFormValues = Omit<Subject, "id">;

const EMPTY: SubjectFormValues = {
  address: "",
  city: "",
  zip_code: "",
  latitude: null,
  longitude: null,
  property_type: "single_family",
  bedrooms: null,
  bathrooms: null,
  square_feet: null,
  lot_size: null,
  year_built: null,
  condition: null,
  parking_spaces: null,
  has_pool: false,
  renovation_notes: "",
  agent_notes: "",
};

function validate(values: SubjectFormValues): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!values.address.trim()) errors.address = "Address is required.";
  if (values.square_feet !== null && values.square_feet <= 0)
    errors.square_feet = "Living area must be greater than zero.";
  if (values.lot_size !== null && values.lot_size < 0)
    errors.lot_size = "Lot size cannot be negative.";
  if (values.bedrooms !== null && (values.bedrooms < 0 || !Number.isInteger(values.bedrooms)))
    errors.bedrooms = "Bedrooms must be a whole number of 0 or more.";
  if (values.bathrooms !== null && values.bathrooms < 0)
    errors.bathrooms = "Bathrooms cannot be negative.";
  if (
    values.year_built !== null &&
    (values.year_built < 1800 || values.year_built > new Date().getFullYear() + 1)
  )
    errors.year_built = "Year built looks out of range.";
  if (values.latitude !== null && Math.abs(values.latitude) > 90)
    errors.latitude = "Latitude must be between -90 and 90.";
  if (values.longitude !== null && Math.abs(values.longitude) > 180)
    errors.longitude = "Longitude must be between -180 and 180.";
  return errors;
}

export function SubjectForm({
  initial,
  onSave,
  saving,
}: {
  initial?: Partial<SubjectFormValues> | null;
  onSave: (values: SubjectFormValues) => void;
  saving?: boolean;
}) {
  const [values, setValues] = useState<SubjectFormValues>({ ...EMPTY, ...(initial ?? {}) });
  const [errors, setErrors] = useState<Record<string, string>>({});

  function set<K extends keyof SubjectFormValues>(key: K, value: SubjectFormValues[K]) {
    setValues((v) => ({ ...v, [key]: value }));
  }

  const numeric = (raw: string): number | null => (raw.trim() === "" ? null : Number(raw));

  // Visual order of the validated fields, used to focus the first error.
  const FIELD_ORDER: (keyof SubjectFormValues)[] = [
    "address", "bedrooms", "bathrooms", "square_feet", "lot_size",
    "year_built", "latitude", "longitude",
  ];

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const found = validate(values);
    setErrors(found);
    if (Object.keys(found).length === 0) {
      onSave(values);
      return;
    }
    // Move focus to the first invalid field so keyboard and screen-reader
    // users land on the problem instead of hunting for it.
    const first = FIELD_ORDER.find((key) => found[key]);
    if (first) document.getElementById(`subject-${first}`)?.focus();
  }

  const inputProps = (key: keyof SubjectFormValues) => ({
    id: `subject-${key}`,
    className: "field-input",
    "aria-invalid": errors[key] ? true : undefined,
    "aria-describedby": errors[key] ? `subject-${key}-error` : undefined,
  });

  return (
    <form onSubmit={handleSubmit} noValidate aria-label="Subject property">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="sm:col-span-2 lg:col-span-1">
          <Field id="subject-address" label="Street address" required error={errors.address}>
            <input
              {...inputProps("address")}
              type="text"
              value={values.address}
              onChange={(e) => set("address", e.target.value)}
              placeholder="12345 Demo Lane"
            />
          </Field>
        </div>
        <Field id="subject-city" label="City">
          <input
            {...inputProps("city")}
            type="text"
            value={values.city ?? ""}
            onChange={(e) => set("city", e.target.value)}
          />
        </Field>
        <Field id="subject-zip_code" label="ZIP code">
          <input
            {...inputProps("zip_code")}
            type="text"
            inputMode="numeric"
            value={values.zip_code ?? ""}
            onChange={(e) => set("zip_code", e.target.value)}
          />
        </Field>
        <Field id="subject-property_type" label="Property type">
          <select
            {...inputProps("property_type")}
            value={values.property_type}
            onChange={(e) => set("property_type", e.target.value)}
          >
            {PROPERTY_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </Field>
        <Field id="subject-bedrooms" label="Bedrooms" error={errors.bedrooms}>
          <input
            {...inputProps("bedrooms")}
            type="number"
            min={0}
            step={1}
            value={values.bedrooms ?? ""}
            onChange={(e) => set("bedrooms", numeric(e.target.value))}
          />
        </Field>
        <Field id="subject-bathrooms" label="Bathrooms" error={errors.bathrooms}>
          <input
            {...inputProps("bathrooms")}
            type="number"
            min={0}
            step={0.5}
            value={values.bathrooms ?? ""}
            onChange={(e) => set("bathrooms", numeric(e.target.value))}
          />
        </Field>
        <Field id="subject-square_feet" label="Living area (sq ft)" error={errors.square_feet}>
          <input
            {...inputProps("square_feet")}
            type="number"
            min={1}
            value={values.square_feet ?? ""}
            onChange={(e) => set("square_feet", numeric(e.target.value))}
          />
        </Field>
        <Field id="subject-lot_size" label="Lot size (sq ft)" error={errors.lot_size}>
          <input
            {...inputProps("lot_size")}
            type="number"
            min={0}
            value={values.lot_size ?? ""}
            onChange={(e) => set("lot_size", numeric(e.target.value))}
          />
        </Field>
        <Field id="subject-year_built" label="Year built" error={errors.year_built}>
          <input
            {...inputProps("year_built")}
            type="number"
            min={1800}
            max={new Date().getFullYear() + 1}
            value={values.year_built ?? ""}
            onChange={(e) => set("year_built", numeric(e.target.value))}
          />
        </Field>
        <Field id="subject-condition" label="Condition">
          <select
            {...inputProps("condition")}
            value={values.condition ?? ""}
            onChange={(e) => set("condition", e.target.value || null)}
          >
            <option value="">Not specified</option>
            {CONDITIONS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </Field>
        <Field id="subject-parking_spaces" label="Parking spaces">
          <input
            {...inputProps("parking_spaces")}
            type="number"
            min={0}
            step={1}
            value={values.parking_spaces ?? ""}
            onChange={(e) => set("parking_spaces", numeric(e.target.value))}
          />
        </Field>
        <div className="flex items-end pb-1">
          {/* Label wraps the checkbox so the whole padded row is tappable. */}
          <label
            htmlFor="subject-has_pool"
            className="flex min-h-[44px] cursor-pointer items-center gap-2 py-2 text-sm"
          >
            <input
              id="subject-has_pool"
              type="checkbox"
              className="h-5 w-5 rounded border-slate-300"
              checked={values.has_pool}
              onChange={(e) => set("has_pool", e.target.checked)}
            />
            Has pool
          </label>
        </div>
        <Field
          id="subject-latitude"
          label="Latitude"
          hint="Optional; enables distance-based similarity."
          error={errors.latitude}
        >
          <input
            {...inputProps("latitude")}
            type="number"
            step="any"
            value={values.latitude ?? ""}
            onChange={(e) => set("latitude", numeric(e.target.value))}
          />
        </Field>
        <Field id="subject-longitude" label="Longitude" error={errors.longitude}>
          <input
            {...inputProps("longitude")}
            type="number"
            step="any"
            value={values.longitude ?? ""}
            onChange={(e) => set("longitude", numeric(e.target.value))}
          />
        </Field>
        <div className="sm:col-span-2 lg:col-span-3">
          <Field id="subject-renovation_notes" label="Renovation notes">
            <textarea
              {...inputProps("renovation_notes")}
              rows={2}
              value={values.renovation_notes ?? ""}
              onChange={(e) => set("renovation_notes", e.target.value)}
            />
          </Field>
        </div>
        <div className="sm:col-span-2 lg:col-span-3">
          <Field id="subject-agent_notes" label="Agent notes (not shown in the report)">
            <textarea
              {...inputProps("agent_notes")}
              rows={2}
              value={values.agent_notes ?? ""}
              onChange={(e) => set("agent_notes", e.target.value)}
            />
          </Field>
        </div>
      </div>
      <div className="mt-4 flex justify-end">
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Saving…" : "Save subject property"}
        </button>
      </div>
    </form>
  );
}
