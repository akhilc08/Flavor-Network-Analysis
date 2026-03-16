interface SkeletonProps {
  className?: string
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div className={`animate-pulse bg-muted/60 rounded ${className}`} />
  )
}

export function CardSkeleton() {
  return (
    <div className="bg-card border border-muted rounded p-6 flex flex-col gap-4 shadow-card">
      <div className="flex justify-between items-start">
        <Skeleton className="h-7 w-32" />
        <Skeleton className="h-5 w-20" />
      </div>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-2 w-full" />
        <Skeleton className="h-[3px] w-full" />
      </div>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-2 w-full" />
        <Skeleton className="h-[3px] w-3/4" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-5 w-16" />
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-5 w-14" />
      </div>
    </div>
  )
}

export function RatePairSkeleton() {
  return (
    <div className="bg-card border border-muted rounded p-6 flex flex-col gap-4 shadow-card">
      <div className="flex justify-between">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-5 w-16" />
      </div>
      <div className="flex gap-8">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-5 w-24" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-5 w-16" />
        <Skeleton className="h-5 w-20" />
      </div>
      <div className="flex gap-2 mt-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-7 w-7 rounded" />
        ))}
      </div>
    </div>
  )
}
