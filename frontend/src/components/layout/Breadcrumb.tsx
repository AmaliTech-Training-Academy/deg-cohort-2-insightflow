"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  uploads:   "Uploads",
  new:       "New upload",
  history:   "Ingestion history",
};

export function Breadcrumb() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  return (
    <nav className="flex text-sm" aria-label="Breadcrumb">
      <ol className="flex items-center gap-1">
        {segments.map((seg, idx) => {
          const href = "/" + segments.slice(0, idx + 1).join("/");
          const isLast = idx === segments.length - 1;
          const label = LABELS[seg] ?? seg.charAt(0).toUpperCase() + seg.slice(1);

          return (
            <li key={href} className="flex items-center gap-1">
              {idx > 0 && (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-300 dark:text-slate-600 shrink-0">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              )}
              {isLast ? (
                <span className="font-medium text-gray-900 dark:text-slate-100">{label}</span>
              ) : (
                <Link href={href} className="text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 transition-colors">
                  {label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
