export default function Loading() {
  return (
    <div className="flex h-[50vh] w-full flex-col items-center justify-center gap-3">
      <div className="h-9 w-9 animate-spin rounded-full border-3 border-ink/10 border-t-forest" />
      <p className="text-xs font-medium uppercase tracking-wider text-ink/40">Loading workspace...</p>
    </div>
  );
}
