"use client";

import { clsx } from "clsx";

export function SeverityBadge({ severity }: { severity: number }) {
  const color = severity >= 7 ? "bg-red-500" : severity >= 4 ? "bg-amber-500" : "bg-green-500";
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium text-white",
        color
      )}
    >
      {severity}/10
    </span>
  );
}
