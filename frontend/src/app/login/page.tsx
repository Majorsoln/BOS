"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Card, CardContent, CardHeader, CardTitle, CardDescription, Input, Label } from "@/components/ui";
import { useAuthStore } from "@/stores/auth-store";
import api from "@/lib/api/client";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuthStore();
  const [apiKey, setApiKey] = useState("");
  const [businessId, setBusinessId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // Temporarily set credentials for the validation call
      localStorage.setItem("bos_api_key", apiKey);
      localStorage.setItem("bos_business_id", businessId);

      const { data } = await api.get("/admin/business");

      if (data.status === "ok") {
        const biz = data.business || data.data || data;
        login(
          apiKey,
          businessId,
          biz.branches?.[0]?.branch_id || "",
          biz.actor_id || "admin",
          biz.name || biz.business_name || "BOS Business",
        );
        router.push("/dashboard");
      } else {
        throw new Error(data.message || "Failed to validate credentials");
      }
    } catch (err: unknown) {
      localStorage.removeItem("bos_api_key");
      localStorage.removeItem("bos_business_id");
      const msg = err instanceof Error ? err.message : "Connection failed. Check your API key and business ID.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 p-4 dark:bg-neutral-900">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-neutral-900 text-2xl font-bold text-white dark:bg-neutral-100 dark:text-neutral-900">
            B
          </div>
          <CardTitle className="text-2xl">Welcome to BOS</CardTitle>
          <CardDescription>
            Enter your API key and Business ID to sign in
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="businessId">Business ID</Label>
              <Input
                id="businessId"
                placeholder="11111111-1111-1111-1111-111111111111"
                value={businessId}
                onChange={(e) => setBusinessId(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="apiKey">API Key</Label>
              <Input
                id="apiKey"
                type="password"
                placeholder="Enter your API key"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                required
              />
            </div>
            {error && (
              <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950 dark:text-red-400">
                {error}
              </div>
            )}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Connecting..." : "Sign In"}
            </Button>
            <p className="mt-4 text-center text-xs text-neutral-400">
              Dev credentials: API Key = <code className="text-neutral-600">dev-admin-key</code>
              <br />
              Business ID = <code className="text-neutral-600">11111111-1111-1111-1111-111111111111</code>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
