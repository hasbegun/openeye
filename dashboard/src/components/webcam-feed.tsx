"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import { Camera, CameraOff, Loader2 } from "lucide-react";
import { getWebSocketUrl } from "@/lib/api";
import type { AnalysisResult } from "@/lib/api";
import { SeverityBadge } from "./severity-badge";

export function WebcamFeed() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const [active, setActive] = useState(false);
  const [lastResult, setLastResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  const startCapture = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      const ws = new WebSocket(getWebSocketUrl());
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.error) {
          setError(data.error);
        } else {
          setLastResult(data);
          setError(null);
        }
        setAnalyzing(false);
      };

      ws.onopen = () => {
        setActive(true);
        setError(null);
        // Send frame every 2 seconds
        intervalRef.current = setInterval(() => {
          if (canvasRef.current && videoRef.current && ws.readyState === WebSocket.OPEN) {
            const ctx = canvasRef.current.getContext("2d");
            if (ctx) {
              canvasRef.current.width = 640;
              canvasRef.current.height = 480;
              ctx.drawImage(videoRef.current, 0, 0, 640, 480);
              canvasRef.current.toBlob(
                (blob) => {
                  if (blob) {
                    ws.send(blob);
                    setAnalyzing(true);
                  }
                },
                "image/jpeg",
                0.8
              );
            }
          }
        }, 2000);
      };

      ws.onerror = () => setError("WebSocket connection failed");
      ws.onclose = () => setActive(false);
    } catch (err) {
      setError("Camera access denied or unavailable");
    }
  }, []);

  const stopCapture = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (videoRef.current?.srcObject) {
      const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
      tracks.forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }
    setActive(false);
    setAnalyzing(false);
  }, []);

  useEffect(() => {
    return () => stopCapture();
  }, [stopCapture]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Live Webcam Analysis</h2>
        <button
          onClick={active ? stopCapture : startCapture}
          className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition ${
            active
              ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
              : "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
          }`}
        >
          {active ? <CameraOff size={16} /> : <Camera size={16} />}
          {active ? "Stop" : "Start Camera"}
        </button>
      </div>

      <div className="relative overflow-hidden rounded-lg border border-gray-800 bg-black">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className="h-[360px] w-full object-cover"
        />
        <canvas ref={canvasRef} className="hidden" />
        {analyzing && (
          <div className="absolute right-3 top-3 flex items-center gap-1.5 rounded-full bg-black/70 px-3 py-1 text-xs text-blue-400">
            <Loader2 size={12} className="animate-spin" />
            Analyzing...
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-800/50 bg-red-900/20 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {lastResult && (
        <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium">{lastResult.description}</p>
              <div className="flex flex-wrap gap-1">
                {lastResult.tags.map((tag) => (
                  <span key={tag} className="rounded bg-gray-800 px-1.5 py-0.5 text-xs text-gray-400">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
            <SeverityBadge severity={lastResult.severity} />
          </div>
        </div>
      )}
    </div>
  );
}
