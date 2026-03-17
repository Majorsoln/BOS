"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, Button, Input, Label, Badge, Toast } from "@/components/ui";
import { getTrialPolicy, setTrialPolicy } from "@/lib/api/saas";
import { ClipboardList, Save, UserCheck } from "lucide-react";

export default function TrialPolicyPage() {
  const queryClient = useQueryClient();
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const policy = useQuery({ queryKey: ["saas", "trial-policy"], queryFn: getTrialPolicy });
  const policyData = policy.data?.data;

  const saveMut = useMutation({
    mutationFn: setTrialPolicy,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saas", "trial-policy"] });
      setToast({ message: "Trial policy updated", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to update policy", variant: "error" }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const data = new FormData(e.target as HTMLFormElement);
    saveMut.mutate({
      default_trial_days: Number(data.get("default_trial_days")),
      max_trial_days: Number(data.get("max_trial_days")),
      grace_period_days: Number(data.get("grace_period_days")),
    });
  }

  return (
    <div>
      <PageHeader
        title="Trial Policy"
        description="Set trial limits — these are guidelines for Agents when onboarding tenants"
      />

      <div className="mx-auto max-w-xl">
        {/* Agent Guidelines Info */}
        <div className="mb-6 rounded-lg border border-bos-purple/20 bg-bos-purple/5 p-4">
          <div className="flex items-center gap-2 mb-2">
            <UserCheck className="h-5 w-5 text-bos-purple" />
            <h3 className="text-sm font-semibold text-bos-purple">Agent Guidelines</h3>
          </div>
          <ul className="text-xs text-bos-silver-dark space-y-1 list-disc list-inside">
            <li>First onboarding/training for new tenants is <strong>FREE</strong></li>
            <li>Agents decide trial length within these limits when onboarding a tenant</li>
            <li>Agents get commission only after platform collects payment from tenant</li>
            <li>Changing these limits only affects new trials — existing trials are not modified</li>
          </ul>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ClipboardList className="h-5 w-5 text-bos-purple" />
                <CardTitle>Trial Settings</CardTitle>
              </div>
              {policyData?.version && (
                <Badge variant="purple">v{policyData.version}</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {policy.isLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-10 animate-pulse rounded bg-neutral-200" />
                ))}
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <Label htmlFor="default_trial_days">Default Trial Days</Label>
                  <p className="text-xs text-bos-silver-dark mb-1">
                    Recommended trial length for agents to offer new tenants
                  </p>
                  <Input
                    id="default_trial_days"
                    name="default_trial_days"
                    type="number"
                    defaultValue={policyData?.default_trial_days ?? 30}
                    min={7}
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="max_trial_days">Maximum Trial Days</Label>
                  <p className="text-xs text-bos-silver-dark mb-1">
                    Absolute maximum an agent can offer (including extensions)
                  </p>
                  <Input
                    id="max_trial_days"
                    name="max_trial_days"
                    type="number"
                    defaultValue={policyData?.max_trial_days ?? 90}
                    min={14}
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="grace_period_days">Grace Period Days</Label>
                  <p className="text-xs text-bos-silver-dark mb-1">
                    Days after trial expires before service is suspended
                  </p>
                  <Input
                    id="grace_period_days"
                    name="grace_period_days"
                    type="number"
                    defaultValue={policyData?.grace_period_days ?? 7}
                    min={0}
                    required
                  />
                </div>

                <Button type="submit" disabled={saveMut.isPending} className="w-full gap-2">
                  <Save className="h-4 w-4" />
                  {saveMut.isPending ? "Saving..." : "Save Policy"}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </div>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
