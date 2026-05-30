import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpenEye — AI Security Monitor",
  description: "Real-time AI-powered CCTV monitoring dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0a0a0a] text-gray-100 antialiased">
        {children}
      </body>
    </html>
  );
}
