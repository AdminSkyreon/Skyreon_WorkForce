"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button, FieldError, Input, Label, Modal } from "./ui";

const schema = z.object({
  current_password: z.string().optional(),
  new_password: z.string().min(8, "Use at least 8 characters"),
});

export function ChangePasswordModal({ forced = false }: { forced?: boolean }) {
  const pathname = usePathname();
  const { user, refreshUser } = useAuth();
  const [open, setOpen] = useState(forced);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

  // Automatically close modal when user navigates to another page
  useEffect(() => {
    if (!forced) {
      setOpen(false);
    }
  }, [pathname, forced]);

  if (!user) return null;

  return (
    <>
      {!forced && (
        <Button variant="ghost" onClick={() => setOpen(true)}>
          Change password
        </Button>
      )}
      <Modal open={open || (forced && user.must_change_password)} title="Change password" onClose={() => !forced && setOpen(false)}>
        <form
          className="space-y-4"
          onSubmit={form.handleSubmit(async (values) => {
            setError("");
            setLoading(true);
            try {
              await api("/auth/change-password", { method: "POST", body: JSON.stringify(values) });
              await refreshUser();
              setOpen(false);
              form.reset();
            } catch (err) {
              setError(err instanceof Error ? err.message : "Unable to change password");
            } finally {
              setLoading(false);
            }
          })}
        >
          {!user.must_change_password && (
            <div>
              <Label>Current password</Label>
              <Input type="password" disabled={loading} {...form.register("current_password")} />
            </div>
          )}
          <div>
            <Label>New password</Label>
            <Input type="password" disabled={loading} {...form.register("new_password")} />
            <FieldError message={form.formState.errors.new_password?.message} />
          </div>
          {error && <p className="text-sm text-red-700">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            {!forced && (
              <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={loading}>
                Cancel
              </Button>
            )}
            <Button type="submit" disabled={loading}>
              {loading ? "Updating..." : "Update password"}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
