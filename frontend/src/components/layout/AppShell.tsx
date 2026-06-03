"use client";

import { Sidebar } from "./Sidebar";
import { Breadcrumb } from "./Breadcrumb";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 dark:bg-slate-950">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="bg-white dark:bg-slate-900 border-b border-gray-200 dark:border-slate-800 px-6 h-12 flex items-center justify-between shrink-0">
          <Breadcrumb />
          <ThemeToggle />
        </header>
        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6 bg-gray-50 dark:bg-slate-950">
          {children}
        </main>
      </div>
    </div>
  );
}
