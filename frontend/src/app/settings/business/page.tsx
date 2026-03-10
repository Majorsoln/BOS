"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from "@/components/ui";
import { getBusinessProfile, updateBusinessProfile } from "@/lib/api/admin";

export default function BusinessSettingsPage() {
  const [profile, setProfile] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    getBusinessProfile()
      .then((res) => {
        const biz = res.business || res.data || res;
        setProfile({
          name: biz.name || "",
          address: biz.address || "",
          city: biz.city || "",
          phone: biz.phone || "",
          email: biz.email || "",
          tax_id: biz.tax_id || "",
          default_currency: biz.default_currency || "KES",
        });
      })
      .catch(() => setMessage("Failed to load business profile"))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      await updateBusinessProfile(profile);
      setMessage("Profile updated successfully");
    } catch {
      setMessage("Failed to update profile");
    } finally {
      setSaving(false);
    }
  }

  const fields = [
    { key: "name", label: "Business Name" },
    { key: "address", label: "Address" },
    { key: "city", label: "City" },
    { key: "phone", label: "Phone" },
    { key: "email", label: "Email" },
    { key: "tax_id", label: "Tax ID / KRA PIN" },
    { key: "default_currency", label: "Default Currency" },
  ];

  return (
    <AppShell>
      <PageHeader title="Business Profile" description="Manage your business information" />
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Business Details</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-neutral-400">Loading...</p>
          ) : (
            <form onSubmit={handleSave} className="space-y-4">
              {fields.map((f) => (
                <div key={f.key} className="space-y-1">
                  <Label htmlFor={f.key}>{f.label}</Label>
                  <Input
                    id={f.key}
                    value={profile[f.key] || ""}
                    onChange={(e) => setProfile({ ...profile, [f.key]: e.target.value })}
                  />
                </div>
              ))}
              {message && (
                <p className={`text-sm ${message.includes("success") ? "text-green-600" : "text-red-600"}`}>
                  {message}
                </p>
              )}
              <Button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save Changes"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
