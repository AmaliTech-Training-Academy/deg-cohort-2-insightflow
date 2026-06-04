"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  badge?: string;
  external?: boolean;
}

interface NavSection {
  section: string;
  items: NavItem[];
}

const NAV: NavSection[] = [
  {
    section: "OPERATIONS",
    items: [
      { href: "/dashboard",       label: "Dashboard",         icon: <DashboardIcon /> },
      { href: "/uploads/new",     label: "New upload",        icon: <UploadIcon /> },
      { href: "/uploads/history", label: "Ingestion history", icon: <HistoryIcon />, badge: "64" },
    ],
  },
  {
    section: "ANALYTICS",
    items: [
      { href: "#", label: "Metabase", icon: <ExternalLinkIcon />, external: true },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  function isActive(href: string) {
    if (href === "#") return false;
    return pathname === href || pathname.startsWith(href + "/");
  }

  const initials = user?.name
    ? user.name.split(" ").slice(0, 2).map((n) => n[0]).join("").toUpperCase()
    : "AR";

  const displayName = user?.name ?? "Amelia Rivera";
  const displayRole = user?.role
    ? user.role.charAt(0).toUpperCase() + user.role.slice(1)
    : "Pipeline Operator";

  return (
    <aside className="w-60 bg-white dark:bg-slate-900 border-r border-gray-200 dark:border-slate-800 flex flex-col shrink-0">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-4 py-4 border-b border-gray-100 dark:border-slate-800">
        <div className="w-8 h-8 bg-green-600 rounded-lg flex items-center justify-center shrink-0">
          <WaveformIcon />
        </div>
        <span className="text-sm font-bold tracking-tight text-gray-900 dark:text-white">
          InsightFlow
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto" aria-label="Main navigation">
        {NAV.map(({ section, items }) => (
          <div key={section}>
            <p className="px-2 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-slate-500 select-none">
              {section}
            </p>
            <ul className="space-y-0.5">
              {items.map((item) => {
                const active = isActive(item.href);
                const baseClass =
                  "flex items-center gap-2.5 w-full px-2 py-2 rounded-md text-sm font-medium transition-colors";
                const activeClass =
                  "bg-green-50 dark:bg-green-950/40 text-green-700 dark:text-green-400";
                const inactiveClass =
                  "text-gray-600 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-800 hover:text-gray-900 dark:hover:text-slate-200";

                const content = (
                  <>
                    <span
                      className={`shrink-0 ${
                        active
                          ? "text-green-600 dark:text-green-400"
                          : "text-gray-400 dark:text-slate-500"
                      }`}
                    >
                      {item.icon}
                    </span>
                    <span className="flex-1">{item.label}</span>
                    {item.badge && (
                      <span className="ml-auto text-xs font-medium px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400">
                        {item.badge}
                      </span>
                    )}
                  </>
                );

                return (
                  <li key={item.href}>
                    {item.external ? (
                      <a
                        href={item.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`${baseClass} ${inactiveClass}`}
                      >
                        {content}
                      </a>
                    ) : (
                      <Link
                        href={item.href}
                        aria-current={active ? "page" : undefined}
                        className={`${baseClass} ${active ? activeClass : inactiveClass}`}
                      >
                        {content}
                      </Link>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-gray-100 dark:border-slate-800 p-3">
        <button
          onClick={logout}
          className="flex items-center gap-2.5 w-full rounded-md px-2 py-2 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors group text-left"
        >
          <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-900 dark:text-slate-100 truncate leading-tight">
              {displayName}
            </p>
            <p className="text-xs text-gray-500 dark:text-slate-400 truncate leading-tight">
              {displayRole}
            </p>
          </div>
          <ChevronIcon />
        </button>
      </div>
    </aside>
  );
}

/* ─── Icons ───────────────────────────────────────────────── */

function WaveformIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3,12 7,12 9,5 12,19 15,8 17,12 21,12" />
    </svg>
  );
}

function DashboardIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 16 12 12 8 16" />
      <line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </svg>
  );
}

function HistoryIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function ExternalLinkIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400 dark:text-slate-500 shrink-0">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}
