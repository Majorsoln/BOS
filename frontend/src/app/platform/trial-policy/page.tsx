"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, Button, Input, Label, Badge, Toast } from "@/components/ui";
import { getTrialPolicy, setTrialPolicy } from "@/lib/api/saas";
import { ClipboardList, Save } from "lucide-react";

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
    const form = e.target as HTMLFormElement;
    const data = new FormData(form);
    saveMut.mutate({
      default_trial_days: Number(data.get("default_trial_days")),
      max_trial_days: Number(data.get("max_trial_days")),
      grace_period_days: Number(data.get("grace_period_days")),
      rate_notice_days: Number(data.get("rate_notice_days")),
    });
  }

  return (
    <div>
      <PageHeader
        title="Trial Policy"
        description="Sera ya trial kwa platform nzima — inaathiri tenants wapya pekee"
      />

      <div className="mx-auto max-w-lg">
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
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-10 animate-pulse rounded bg-neutral-200" />
                ))}
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <Label htmlFor="default_trial_days">Default Trial Days</Label>
                  <p className="text-xs text-bos-silver-dark mb-1">Siku za trial kwa tenant mpya</p>
                  <Input
                    id="default_trial_days"
                    name="default_trial_days"
                    type="number"
                    defaultValue={policyData?.default_trial_days ?? 180}
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="max_trial_days">Max Trial Days</Label>
                  <p className="text-xs text-bos-silver-dark mb-1">Kiwango cha juu (pamoja na referral + promo bonuses)</p>
                  <Input
                    id="max_trial_days"
                    name="max_trial_days"
                    type="number"
                    defaultValue={policyData?.max_trial_days ?? 365}
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="grace_period_days">Grace Period Days</Label>
                  <p className="text-xs text-bos-silver-dark mb-1">Siku za neema baada ya trial kuisha</p>
                  <Input
                    id="grace_period_days"
                    name="grace_period_days"
                    type="number"
                    defaultValue={policyData?.grace_period_days ?? 7}
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="rate_notice_days">Rate Notice Days</Label>
                  <p className="text-xs text-bos-silver-dark mb-1">Siku za notisi kabla ya kubadilisha bei (min 90)</p>
                  <Input
                    id="rate_notice_days"
                    name="rate_notice_days"
                    type="number"
                    defaultValue={policyData?.rate_notice_days ?? 90}
                    min={90}
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
