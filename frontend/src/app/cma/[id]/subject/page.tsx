"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Card, ErrorBox } from "@/components/ui";
import { SubjectForm, type SubjectFormValues } from "@/components/SubjectForm";
import { useCma } from "../cma-context";

export default function SubjectPage() {
  const { cma, reload } = useCma();
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleSave(values: SubjectFormValues) {
    setSaving(true);
    setError(null);
    try {
      await api.saveSubject(cma.id, values);
      if (cma.title === "Untitled CMA" && values.address.trim()) {
        await api.updateCma(cma.id, { title: `CMA — ${values.address.trim()}` });
      }
      reload();
      setSaved(true);
      router.push(`/cma/${cma.id}/comparables`);
    } catch (e) {
      setError((e as ApiError).message);
      setSaving(false);
    }
  }

  return (
    <Card title="Subject property">
      <p className="mb-4 text-sm text-slate-500">
        Details about the property being valued. The more complete this is, the more
        similarity components and suggested adjustments can be calculated — missing
        fields are skipped, never guessed.
      </p>
      {error && <ErrorBox message={error} />}
      {saved && (
        <p role="status" className="sr-only">
          Subject saved
        </p>
      )}
      <SubjectForm initial={cma.subject} onSave={handleSave} saving={saving} />
    </Card>
  );
}
