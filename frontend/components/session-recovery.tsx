"use client";

import { useState } from "react";
import { Button, Card } from "@/components/ui";
import type { SessionError } from "@/lib/auth";

export function SessionRecovery({
  reason,
  onRetry,
  onLogout,
}: {
  reason: Exclude<SessionError, null>;
  onRetry: () => void;
  onLogout: () => Promise<void>;
}) {
  const [signingOut, setSigningOut] = useState(false);

  const isRateLimited = reason === "rate_limited";

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper p-6">
      <Card className="w-full max-w-md space-y-4 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-copper">
          {isRateLimited ? "Server Busy" : "Connection Issue"}
        </p>
        <h2 className="font-display text-2xl text-ink">
          {isRateLimited ? "The server is temporarily busy" : "Could not reach the server"}
        </h2>
        <p className="text-sm text-ink/70">
          {isRateLimited
            ? "You are still signed in. Wait a few seconds for the rate limit to clear, then click Retry."
            : "Your session is still intact. Check your connection or wait a moment for the server to wake up, then click Retry."}
        </p>
        <div className="flex items-center justify-center gap-3 pt-2">
          <Button onClick={onRetry}>Retry</Button>
          <Button
            variant="outline"
            loading={signingOut}
            onClick={() => {
              setSigningOut(true);
              void onLogout().finally(() => setSigningOut(false));
            }}
          >
            Sign out
          </Button>
        </div>
      </Card>
    </div>
  );
}
