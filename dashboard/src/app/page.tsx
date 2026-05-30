"use client";

import { useEffect, useState } from "react";
import { Eye, Shield, Activity, Bell } from "lucide-react";
import { fetchAlerts, fetchHealth, fetchAlertCount } from "@/lib/api";
import type { Alert, HealthStatus } from "@/lib/api";
import { AlertCard } from "@/components/alert-card";
import { WebcamFeed } from "@/components/webcam-feed";

export default function Home() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [alertCount, setAlertCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [alertsData, healthData, countData] = await Promise.all([
          fetchAlerts({ limit: 20 }),
          fetchHealth(),
          fetchAlertCount(),
        ]);
        setAlerts(alertsData);
        setHealth(healthData);
        setAlertCount(countData);
        setError(null);
      } catch (err) {
        setError("Failed to connect to gateway. Is the backend running?");
      }
    }
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8 flex items-center gap-3">
        <Eye className="text-emerald-400" size={32} />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">OpenEye</h1>
          <p className="text-sm text-gray-400">AI-Powered Security Monitor</p>
        </div>
      </div>

      {/* Status Cards */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatusCard
          icon={<Activity size={20} />}
          label="System"
          value={health ? "Online" : "Offline"}
          color={health ? "text-emerald-400" : "text-red-400"}
        />
        <StatusCard
          icon={<Shield size={20} />}
          label="Version"
          value={health?.version || "—"}
          color="text-blue-400"
        />
        <StatusCard
          icon={<Bell size={20} />}
          label="Total Alerts"
          value={String(alertCount)}
          color="text-amber-400"
        />
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-amber-800/50 bg-amber-900/20 px-4 py-3 text-sm text-amber-400">
          {error}
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        {/* Webcam */}
        <section>
          <WebcamFeed />
        </section>

        {/* Alerts Feed */}
        <section>
          <h2 className="mb-4 text-lg font-semibold">Recent Alerts</h2>
          {alerts.length === 0 ? (
            <div className="rounded-lg border border-gray-800 bg-gray-900/30 px-4 py-12 text-center text-sm text-gray-500">
              No alerts yet. System is monitoring.
            </div>
          ) : (
            <div className="space-y-3">
              {alerts.map((alert) => (
                <AlertCard key={alert.alert_id} alert={alert} />
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function StatusCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
      <div className="flex items-center gap-3">
        <div className={color}>{icon}</div>
        <div>
          <p className="text-xs text-gray-400">{label}</p>
          <p className={`text-lg font-semibold ${color}`}>{value}</p>
        </div>
      </div>
    </div>
  );
}
