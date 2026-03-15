"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Toast, Badge,
} from "@/components/ui";
import { setReferralPolicy, generateReferralCode, submitReferral, qualifyReferral } from "@/lib/api/saas";
import { Gift, Code, UserPlus, Award, Save, Copy, Check } from "lucide-react";

export default function ReferralsPage() {
  const queryClient = useQueryClient();
  const [showUpdatePolicy, setShowUpdatePolicy] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);
  const [generatedCode, setGeneratedCode] = useState("");
  const [copied, setCopied] = useState(false);
  const [qualifyResult, setQualifyResult] = useState<Record<string, unknown> | null>(null);

  const policyMut = useMutation({
    mutationFn: setReferralPolicy,
    onSuccess: () => { setShowUpdatePolicy(false); setToast({ message: "Referral policy updated", variant: "success" }); },
    onError: () => setToast({ message: "Failed to update policy", variant: "error" }),
  });

  const generateMut = useMutation({
    mutationFn: generateReferralCode,
    onSuccess: (res) => {
      setGeneratedCode(res.data?.code ?? res.code ?? "");
      setToast({ message: "Referral code generated", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to generate code", variant: "error" }),
  });

  const submitMut = useMutation({
    mutationFn: submitReferral,
    onSuccess: () => setToast({ message: "Referral submitted", variant: "success" }),
    onError: () => setToast({ message: "Failed to submit referral", variant: "error" }),
  });

  const qualifyMut = useMutation({
    mutationFn: qualifyReferral,
    onSuccess: (res) => {
      setQualifyResult(res.data ?? res);
      setToast({ message: "Referral qualified", variant: "success" });
    },
    onError: () => setToast({ message: "Failed to qualify referral", variant: "error" }),
  });

  function handleUpdatePolicy(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    policyMut.mutate({
      referrer_reward_days: Number(d.get("referrer_reward_days")),
      referee_bonus_days: Number(d.get("referee_bonus_days")),
      qualification_days: Number(d.get("qualification_days")),
      qualification_min_transactions: Number(d.get("qualification_min_transactions")),
      max_referrals_per_year: Number(d.get("max_referrals_per_year")),
      champion_threshold: Number(d.get("champion_threshold")),
    });
  }

  function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    generateMut.mutate({
      business_id: d.get("business_id") as string,
      business_name: d.get("business_name") as string,
    });
  }

  function handleSubmitRef(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    submitMut.mutate({
      referral_code: d.get("referral_code") as string,
      referee_business_id: d.get("referee_business_id") as string,
      referee_phone: d.get("referee_phone") as string || undefined,
    });
  }

  function handleQualify(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const d = new FormData(form);
    qualifyMut.mutate({ referee_business_id: d.get("referee_business_id") as string });
  }

  function copyCode() {
    navigator.clipboard.writeText(generatedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div>
      <PageHeader
        title="Referral Program"
        description="Manage the BOS referral program and track referrals"
        actions={
          <Button variant="outline" onClick={() => setShowUpdatePolicy(true)} className="gap-2">
            <Save className="h-4 w-4" />
            Update Policy
          </Button>
        }
      />

      {/* Action Cards */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Generate Code */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Code className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Generate Code</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleGenerate} className="space-y-3">
              <div>
                <Label htmlFor="gen_biz_id">Business ID</Label>
                <Input id="gen_biz_id" name="business_id" required className="mt-1" />
              </div>
              <div>
                <Label htmlFor="gen_biz_name">Business Name</Label>
                <Input id="gen_biz_name" name="business_name" placeholder="e.g. Mama Mboga" required className="mt-1" />
              </div>
              <Button type="submit" disabled={generateMut.isPending} className="w-full">
                {generateMut.isPending ? "Generating..." : "Generate"}
              </Button>
            </form>

            {generatedCode && (
              <div className="mt-4 flex items-center gap-2 rounded-lg bg-bos-purple-light p-3">
                <code className="flex-1 font-mono text-sm font-bold text-bos-purple">{generatedCode}</code>
                <button onClick={copyCode} className="text-bos-purple hover:text-bos-purple-dark">
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Submit Referral */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <UserPlus className="h-5 w-5 text-bos-purple" />
              <CardTitle className="text-base">Submit Referral</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmitRef} className="space-y-3">
              <div>
                <Label htmlFor="ref_code">Referral Code</Label>
                <Input id="ref_code" name="referral_code" placeholder="e.g. BOS-MAMA-7X3K" required className="mt-1" />
              </div>
              <div>
                <Label htmlFor="ref_biz_id">Referee Business ID</Label>
                <Input id="ref_biz_id" name="referee_business_id" required className="mt-1" />
              </div>
              <div>
                <Label htmlFor="ref_phone">Phone (optional)</Label>
                <Input id="ref_phone" name="referee_phone" placeholder="+254..." className="mt-1" />
              </div>
              <Button type="submit" disabled={submitMut.isPending} className="w-full">
                {submitMut.isPending ? "Submitting..." : "Submit"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Qualify Referral */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Award className="h-5 w-5 text-bos-gold" />
              <CardTitle className="text-base">Qualify Referral</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleQualify} className="space-y-3">
              <div>
                <Label htmlFor="qual_biz_id">Referee Business ID</Label>
                <Input id="qual_biz_id" name="referee_business_id" required className="mt-1" />
              </div>
              <Button type="submit" disabled={qualifyMut.isPending} className="w-full">
                {qualifyMut.isPending ? "Qualifying..." : "Qualify"}
              </Button>
            </form>

            {qualifyResult && (
              <div className="mt-4 space-y-1 rounded-lg bg-bos-gold-light p-3 text-sm">
                <p>Status: <strong>{qualifyResult.status as string}</strong></p>
                {qualifyResult.is_champion ? (
                  <Badge variant="gold">BOS Champion</Badge>
                ) : null}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Update Policy Dialog */}
      <FormDialog
        open={showUpdatePolicy}
        onClose={() => setShowUpdatePolicy(false)}
        title="Update Referral Policy"
        onSubmit={handleUpdatePolicy}
        submitLabel="Save Policy"
        loading={policyMut.isPending}
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="referrer_reward_days">Referrer Reward (days)</Label>
            <Input id="referrer_reward_days" name="referrer_reward_days" type="number" defaultValue={30} required className="mt-1" />
          </div>
          <div>
            <Label htmlFor="referee_bonus_days">Referee Bonus (days)</Label>
            <Input id="referee_bonus_days" name="referee_bonus_days" type="number" defaultValue={30} required className="mt-1" />
          </div>
          <div>
            <Label htmlFor="qualification_days">Qualification Days</Label>
            <Input id="qualification_days" name="qualification_days" type="number" defaultValue={30} required className="mt-1" />
          </div>
          <div>
            <Label htmlFor="qualification_min_transactions">Min Transactions</Label>
            <Input id="qualification_min_transactions" name="qualification_min_transactions" type="number" defaultValue={10} required className="mt-1" />
          </div>
          <div>
            <Label htmlFor="max_referrals_per_year">Max Referrals/Year</Label>
            <Input id="max_referrals_per_year" name="max_referrals_per_year" type="number" defaultValue={12} required className="mt-1" />
          </div>
          <div>
            <Label htmlFor="champion_threshold">Champion Threshold</Label>
            <Input id="champion_threshold" name="champion_threshold" type="number" defaultValue={10} required className="mt-1" />
          </div>
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
