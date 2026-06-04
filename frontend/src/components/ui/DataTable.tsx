interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  className?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  className = "",
}: DataTableProps<T>) {
  return (
    <div className={`overflow-x-auto rounded-lg border border-gray-200 dark:border-slate-700 ${className}`}>
      <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-700 text-sm">
        <thead className="bg-gray-50 dark:bg-slate-700/50">
          <tr>
            {columns.map((col) => (
              <th
                key={String(col.key)}
                className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400"
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-slate-700 bg-white dark:bg-slate-800">
          {rows.map((row) => (
            <tr key={rowKey(row)} className="hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors">
              {columns.map((col) => (
                <td key={String(col.key)} className="px-4 py-3 text-gray-700 dark:text-slate-300">
                  {col.render
                    ? col.render(row)
                    : String((row as Record<string, unknown>)[String(col.key)] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
