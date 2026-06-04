"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

const TRUST_POINTS = [
  {
    text: "Unified dashboard across POS, inventory, and online orders",
  },
  {
    text: "Automated ingestion with real-time status tracking per job",
  },
  {
    text: "Built-in retry logic, error reporting, and audit history",
  },
];

interface AuthLayoutProps {
  children: React.ReactNode;
}

export function AuthLayout({ children }: AuthLayoutProps) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <div className="min-h-screen flex">
      {/* ── Brand panel — lg+ only ──────────────────────────── */}
      <div className="hidden lg:flex lg:w-[45%] relative overflow-hidden bg-gradient-to-br from-green-950 via-green-900 to-emerald-950 flex-col">
        {/* Animated mesh blobs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-32 -left-32 w-[28rem] h-[28rem] bg-green-500/20 rounded-full blur-3xl animate-pulse" />
          <div className="absolute top-1/2 -right-40 w-96 h-96 bg-emerald-400/15 rounded-full blur-3xl animate-pulse [animation-delay:2s]" />
          <div className="absolute -bottom-24 left-1/4 w-80 h-80 bg-green-600/25 rounded-full blur-3xl animate-pulse [animation-delay:4s]" />
          {/* Subtle grid overlay */}
          <div
            className="absolute inset-0 opacity-[0.06]"
            style={{
              backgroundImage:
                "linear-gradient(rgba(255,255,255,.2) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.2) 1px, transparent 1px)",
              backgroundSize: "48px 48px",
            }}
          />
        </div>

        {/* Content */}
        <div className="relative z-10 flex flex-col h-full px-10 py-10 justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-white/10 rounded-xl flex items-center justify-center ring-1 ring-white/20">
              <BrandIcon />
            </div>
            <span className="text-white font-bold tracking-tight">InsightFlow</span>
          </div>

          {/* Main copy */}
          <div>
            <p className="text-green-400 text-xs font-semibold uppercase tracking-widest mb-4">
              Retail Analytics
            </p>
            <h1 className="text-[2rem] font-bold text-white leading-snug mb-8">
              Operations console for your retail data pipeline.
            </h1>

            <ul className="space-y-4">
              {TRUST_POINTS.map(({ text }) => (
                <li key={text} className="flex items-start gap-3">
                  <span className="mt-0.5 w-5 h-5 rounded-full bg-green-500/30 ring-1 ring-green-400/40 flex items-center justify-center shrink-0">
                    <CheckIcon />
                  </span>
                  <p className="text-green-100/75 text-sm leading-relaxed">{text}</p>
                </li>
              ))}
            </ul>
          </div>

          <p className="text-green-800 text-xs">© 2025 InsightFlow</p>
        </div>
      </div>

      {/* ── Form column ──────────────────────────────────────── */}
      <div className="flex-1 flex flex-col bg-white dark:bg-slate-900 min-h-screen">
        {/* Mobile brand bar */}
        <div className="lg:hidden flex items-center justify-between px-5 py-3.5 border-b border-gray-100 dark:border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-green-600 rounded-lg flex items-center justify-center shrink-0">
              <BrandIconSmall />
            </div>
            <span className="text-sm font-bold text-gray-900 dark:text-white tracking-tight">
              InsightFlow
            </span>
          </div>
          <ThemeToggleButton theme={theme} setTheme={setTheme} mounted={mounted} />
        </div>

        {/* Form area */}
        <div className="flex-1 flex items-center justify-center px-5 py-12">
          <div className="w-full max-w-[400px]">
            {/* Desktop theme toggle */}
            <div className="hidden lg:flex justify-end mb-8">
              <ThemeToggleButton theme={theme} setTheme={setTheme} mounted={mounted} />
            </div>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

function ThemeToggleButton({
  theme,
  setTheme,
  mounted,
}: {
  theme: string | undefined;
  setTheme: (t: string) => void;
  mounted: boolean;
}) {
  if (!mounted) return <div className="w-8 h-8" />;
  const isDark = theme === "dark";
  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="p-1.5 rounded-md text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
    >
      {isDark ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}

function BrandIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3,12 7,12 9,5 12,19 15,8 17,12 21,12" />
    </svg>
  );
}

function BrandIconSmall() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3,12 7,12 9,5 12,19 15,8 17,12 21,12" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}
