const widths = ["w-4/5", "w-3/5", "w-2/3"];

function Bar({ className = "h-3 w-full" }) {
  return <div className={`skeleton-shimmer rounded-md ${className}`} />;
}

function Card({ lines = 2, tall = false }) {
  return (
    <div className={`rounded-xl border border-neutral-800 bg-neutral-900/80 p-5 ${tall ? "h-56" : "h-28"}`}>
      <Bar className="h-3 w-24 mb-5" />
      <div className="space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <Bar key={i} className={`h-2.5 ${widths[i % widths.length]}`} />
        ))}
      </div>
    </div>
  );
}

export default function PageLoading({ page = "page", variant = "cards" }) {
  return (
    <div className="flex-1 h-full overflow-hidden p-8" role="status" aria-live="polite">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <div className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-violet-500/20 bg-violet-500/10">
            <span className="absolute h-2 w-2 rounded-full bg-violet-400 animate-ping" />
            <span className="h-2 w-2 rounded-full bg-violet-400" />
          </div>
          <div>
            <p className="text-sm font-medium text-neutral-200">Loading {page}</p>
            <p className="text-xs text-neutral-500 mt-0.5">Syncing your latest career data</p>
          </div>
        </div>

        <div className="space-y-5 animate-[fadeIn_.2s_ease-out]">
          <Bar className="h-7 w-48" />
          {variant === "dashboard" && (
            <>
              <div className="grid grid-cols-3 gap-4">
                <Card /><Card /><Card />
              </div>
              <div className="grid grid-cols-2 gap-5">
                <Card tall lines={4} /><Card tall lines={4} />
              </div>
            </>
          )}
          {variant === "list" && (
            <div className="space-y-3">
              <Card lines={2} /><Card lines={2} /><Card lines={2} /><Card lines={2} />
            </div>
          )}
          {variant === "form" && (
            <>
              <Bar className="h-3 w-2/3" />
              <div className="flex gap-3"><Bar className="h-10 w-40" /><Bar className="h-10 w-48" /></div>
              <Card lines={3} /><Card lines={3} />
            </>
          )}
          {variant === "chat" && (
            <div className="max-w-3xl space-y-6 pt-8">
              <div className="ml-auto w-2/3"><Card lines={2} /></div>
              <div className="w-4/5"><Card lines={3} /></div>
              <div className="ml-auto w-1/2"><Card lines={2} /></div>
            </div>
          )}
        </div>
        <span className="sr-only">Loading {page}</span>
      </div>
    </div>
  );
}
