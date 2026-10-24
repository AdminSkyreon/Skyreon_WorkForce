"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { SkyreonLogo } from "@/components/skyreon-logo";
import { Button, FieldError, Input, Label, Modal } from "@/components/ui";
import { useAuth } from "@/lib/auth";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1, "Password is required"),
});

export default function LoginPage() {
  const router = useRouter();
  const { login, user } = useAuth();
  const [error, setError] = useState("");
  const [forgotOpen, setForgotOpen] = useState(false);
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (!user) return;
    router.replace(user.role === "employee" ? "/employee/dashboard" : "/admin/dashboard");
  }, [user, router]);

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="relative hidden overflow-hidden bg-ink p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-20 top-20 h-72 w-72 rounded-full bg-copper/20 blur-3xl" />
        <div className="w-fit rounded-2xl bg-white px-4 py-3">
          <SkyreonLogo className="h-10" />
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-copper">Internal systems</p>
          <h1 className="mt-3 font-display text-6xl leading-tight">Workforce Portal</h1>
          <p className="mt-6 max-w-md text-lg text-white/70">
            Projects, timers, timesheets, leave and holidays — kept on the server, owned by the people who do the work.
          </p>
        </div>
        <p className="text-sm text-white/40">Admin-created accounts only.</p>
      </section>
      <section className="flex items-center justify-center bg-paper p-8">
        <div className="w-full max-w-md rounded-[2rem] bg-white p-8 shadow-card">
          <SkyreonLogo className="mb-6 h-8" />
          <p className="text-xs uppercase tracking-[0.3em] text-copper">Sign in</p>
          <h2 className="mt-2 font-display text-4xl">Welcome back</h2>
          <form
            className="mt-8 space-y-4"
            onSubmit={form.handleSubmit(async (values) => {
              setError("");
              try {
                const user = await login(values.email, values.password);
                router.push(user.role === "employee" ? "/employee/dashboard" : "/admin/dashboard");
              } catch (err) {
                setError(err instanceof Error ? err.message : "Unable to sign in");
              }
            })}
          >
            <div>
              <Label>Email</Label>
              <Input type="email" {...form.register("email")} />
              <FieldError message={form.formState.errors.email?.message} />
            </div>
            <div>
              <Label>Password</Label>
              <Input type="password" {...form.register("password")} />
              <FieldError message={form.formState.errors.password?.message} />
            </div>
            {error && <p className="text-sm text-red-700">{error}</p>}
            <Button type="submit" className="w-full">
              Continue
            </Button>
          </form>
          <button className="mt-4 text-sm text-forest underline" onClick={() => setForgotOpen(true)}>
            Forgot password?
          </button>
        </div>
      </section>
      <Modal open={forgotOpen} title="Reset your password" onClose={() => setForgotOpen(false)}>
        <p className="text-sm leading-6 text-ink/70">
          Password resets are handled by an administrator. Ask them to open your employee record and use
          <strong> Reset password</strong>. You will be asked to choose a new password on next login.
        </p>
        <Button className="mt-4" onClick={() => setForgotOpen(false)}>
          Understood
        </Button>
      </Modal>
    </div>
  );
}
