interface LoadingSkeletonProps {
  rows?: number;
  className?: string;
}

export function LoadingSkeleton({ rows = 4, className = "" }: LoadingSkeletonProps) {
  return (
    <div className={`space-y-3 ${className}`} aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-4 rounded bg-gray-200 animate-pulse"
          style={{ width: `${85 - (i % 3) * 10}%` }}
        />
      ))}
    </div>
  );
}
