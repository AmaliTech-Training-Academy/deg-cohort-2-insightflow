"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  uploads: "Uploads",
  new: "New Upload",
  history: "History",
};

export function Breadcrumb() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  return (
    <nav className="flex text-sm text-gray-500 mb-6" aria-label="Breadcrumb">
      <ol className="flex items-center space-x-1">
        {segments.map((seg, idx) => {
          const href = "/" + segments.slice(0, idx + 1).join("/");
          const isLast = idx === segments.length - 1;
          const label = LABELS[seg] ?? seg.charAt(0).toUpperCase() + seg.slice(1);

          return (
            <li key={href} className="flex items-center">
              {idx > 0 && <span className="mx-1 text-gray-400">/</span>}
              {isLast ? (
                <span className="text-gray-900 font-medium">{label}</span>
              ) : (
                <Link href={href} className="hover:text-gray-700 transition-colors">
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
