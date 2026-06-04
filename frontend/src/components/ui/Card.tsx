interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
}

export function Card({ children, className = "", title }: CardProps) {
  return (
    <div className={`rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm ${className}`}>
      {title && (
        <div className="border-b border-gray-200 dark:border-slate-700 px-5 py-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">{title}</h3>
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}
