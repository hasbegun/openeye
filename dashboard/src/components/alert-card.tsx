"use client";

import { AlertTriangle, Clock } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { SeverityBadge } from "./severity-badge";
import type { Alert } from "@/lib/api";

export function AlertCard({ alert }: { alert: Alert }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4 transition hover:border-gray-700">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <AlertTriangle
            className={alert.severity >= 7 ? "text-red-400" : "text-amber-400"}
            size={20}
          />
          <div className="space-y-1">
            <p className="text-sm font-medium text-gray-100">{alert.description}</p>
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <Clock size={12} />
              <span>{formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}</span>
              <span className="text-gray-600">|</span>
              <span>{alert.source_id}</span>
            </div>
            {alert.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 pt-1">
                {alert.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded bg-gray-800 px-1.5 py-0.5 text-xs text-gray-400"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
        <SeverityBadge severity={alert.severity} />
      </div>
    </div>
  );
}
