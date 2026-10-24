import { Card } from "@/components/ui";

export function PageSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-8 w-48 rounded-lg bg-mist" />
      <div className="h-4 w-72 max-w-full rounded bg-mist" />
      <Card className="space-y-3 p-4">
        <div className="h-4 w-full rounded bg-mist" />
        <div className="h-4 w-5/6 rounded bg-mist" />
        <div className="h-4 w-4/6 rounded bg-mist" />
      </Card>
      <Card className="h-64 p-0">
        <div className="h-10 bg-mist" />
        <div className="space-y-2 p-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-8 rounded bg-mist/80" />
          ))}
        </div>
      </Card>
    </div>
  );
}
