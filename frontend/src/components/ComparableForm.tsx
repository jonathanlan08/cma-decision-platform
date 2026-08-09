"use client";

import { useState } from "react";
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

export interface ComparableFormValues {
  address: string;
  city: string;
  zip_code: string;
  property_type: string;
  sale_price: number | null;
  sale_date: string;
  square_feet: number | null;
  lot_size: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  year_built: number | null;
  condition: string | null;
  parking_spaces: number | null;
  has_pool: boolean;
  distance_from_subject: number | null;
  notes: string;
}

const EMPTY: ComparableFormValues = {
  address: "",
  city: "",
  zip_code: "",
  property_type: "single_family",
  sale_price: null,
  sale_date: "",
  square_feet: null,
  lot_size: null,
  bedrooms: null,
  bathrooms: null,
  year_built: null,
  condition: null,
  parking_spaces: null,
  has_pool: false,
  distance_from_subject: null,
  notes: "",
};

function validate(v: ComparableFormValues): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!v.address.trim()) errors.address = "Address is required.";
  if (v.sale_price === null || v.sale_price <= 0)
    errors.sale_price = "Sale price must be greater than zero.";
  if (!v.sale_date) errors.sale_date = "Sale date is required.";
  else if (new Date(v.sale_date) > new Date())
    errors.sale_date = "Sale date cannot be in the future.";
  if (v.square_feet === null || v.square_feet <= 0)
    errors.square_feet = "Living area must be greater than zero.";
  if (v.bedrooms === null || v.bedrooms < 0 || !Number.isInteger(v.bedrooms))
    errors.bedrooms = "Bedrooms must be a whole number of 0 or more.";
  if (v.bathrooms === null || v.bathrooms < 0)
    errors.bathrooms = "Bathrooms are required (0 or more).";
  return errors;
}

export function ComparableForm({
  onSave,
  saving,
}: {
  onSave: (values: ComparableFormValues) => void;
  saving?: boolean;
}) {
  const [values, setValues] = useState<ComparableFormValues>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});

  function set<K extends keyof ComparableFormValues>(key: K, value: ComparableFormValues[K]) {
    setValues((v) => ({ ...v, [key]: value }));
  }
  const numeric = (raw: string): number | null => (raw.trim() === "" ? null : Number(raw));

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const found = validate(values);
    setErrors(found);
    if (Object.keys(found).length === 0) {
      onSave(values);
      setValues(EMPTY);
    }
  }

  const props = (key: keyof ComparableFormValues) => ({
    id: `comp-${key}`,
    className: "field-input",
    "aria-invalid": errors[key] ? true : undefined,
  });

  return (
    <form onSubmit={handleSubmit} noValidate aria-label="Add comparable manually">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2">
          <Field id="comp-address" label="Address" required error={errors.address}>
            <input {...props("address")} type="text" value={values.address}
              onChange={(e) => set("address", e.target.value)} />
          </Field>
        </div>
        <Field id="comp-city" label="City">
          <input {...props("city")} type="text" value={values.city}
            onChange={(e) => set("city", e.target.value)} />
        </Field>
        <Field id="comp-zip_code" label="ZIP">
          <input {...props("zip_code")} type="text" value={values.zip_code}
            onChange={(e) => set("zip_code", e.target.value)} />
        </Field>
        <Field id="comp-sale_price" label="Sale price ($)" required error={errors.sale_price}>
          <input {...props("sale_price")} type="number" min={1} value={values.sale_price ?? ""}
            onChange={(e) => set("sale_price", numeric(e.target.value))} />
        </Field>
        <Field id="comp-sale_date" label="Sale date" required error={errors.sale_date}>
          <input {...props("sale_date")} type="date" value={values.sale_date}
            onChange={(e) => set("sale_date", e.target.value)} />
        </Field>
        <Field id="comp-square_feet" label="Living area (sq ft)" required error={errors.square_feet}>
          <input {...props("square_feet")} type="number" min={1} value={values.square_feet ?? ""}
            onChange={(e) => set("square_feet", numeric(e.target.value))} />
        </Field>
        <Field id="comp-lot_size" label="Lot size (sq ft)">
          <input {...props("lot_size")} type="number" min={0} value={values.lot_size ?? ""}
            onChange={(e) => set("lot_size", numeric(e.target.value))} />
        </Field>
        <Field id="comp-bedrooms" label="Bedrooms" required error={errors.bedrooms}>
          <input {...props("bedrooms")} type="number" min={0} step={1} value={values.bedrooms ?? ""}
            onChange={(e) => set("bedrooms", numeric(e.target.value))} />
        </Field>
        <Field id="comp-bathrooms" label="Bathrooms" required error={errors.bathrooms}>
          <input {...props("bathrooms")} type="number" min={0} step={0.5}
            value={values.bathrooms ?? ""}
            onChange={(e) => set("bathrooms", numeric(e.target.value))} />
        </Field>
        <Field id="comp-year_built" label="Year built">
          <input {...props("year_built")} type="number" min={1800} value={values.year_built ?? ""}
            onChange={(e) => set("year_built", numeric(e.target.value))} />
        </Field>
        <Field id="comp-condition" label="Condition">
          <select {...props("condition")} value={values.condition ?? ""}
            onChange={(e) => set("condition", e.target.value || null)}>
            <option value="">Not specified</option>
            {CONDITIONS.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </Field>
        <Field id="comp-property_type" label="Property type">
          <select {...props("property_type")} value={values.property_type}
            onChange={(e) => set("property_type", e.target.value)}>
            {PROPERTY_TYPES.map((t) => (
              <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
            ))}
          </select>
        </Field>
        <Field id="comp-parking_spaces" label="Parking spaces">
          <input {...props("parking_spaces")} type="number" min={0} step={1}
            value={values.parking_spaces ?? ""}
            onChange={(e) => set("parking_spaces", numeric(e.target.value))} />
        </Field>
        <Field id="comp-distance_from_subject" label="Distance from subject (mi)">
          <input {...props("distance_from_subject")} type="number" min={0} step={0.1}
            value={values.distance_from_subject ?? ""}
            onChange={(e) => set("distance_from_subject", numeric(e.target.value))} />
        </Field>
        <div className="flex items-end pb-2">
          <label htmlFor="comp-has_pool" className="flex items-center gap-2 text-sm">
            <input id="comp-has_pool" type="checkbox" className="h-4 w-4 rounded border-slate-300"
              checked={values.has_pool} onChange={(e) => set("has_pool", e.target.checked)} />
            Has pool
          </label>
        </div>
        <div className="sm:col-span-2 lg:col-span-4">
          <Field id="comp-notes" label="Notes">
            <input {...props("notes")} type="text" value={values.notes}
              onChange={(e) => set("notes", e.target.value)} />
          </Field>
        </div>
      </div>
      <div className="mt-3 flex justify-end">
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Adding…" : "Add comparable"}
        </button>
      </div>
    </form>
  );
}
