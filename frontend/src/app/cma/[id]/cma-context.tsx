"use client";

import { createContext, useContext } from "react";
import type { CMADetail } from "@/lib/types";

export const CmaContext = createContext<{ cma: CMADetail; reload: () => void } | null>(null);

export function useCma() {
  const ctx = useContext(CmaContext);
  if (!ctx) throw new Error("useCma must be used inside the CMA layout");
  return ctx;
}
