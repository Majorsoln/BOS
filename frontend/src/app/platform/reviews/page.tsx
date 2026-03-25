"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Input,
  Select,
  Badge,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Textarea,
} from "@/components/ui";
import { getPendingProfiles } from "@/lib/api/platform";
import { reviewComplianceProfile, activateComplianceProfile } from "@/lib/api/saas";
import {
  ClipboardCheck,
  RefreshCw,
  CheckCircle,
  XCircle,
  Eye,
  Clock,
  MapPin,
  Building,
  Shield,
  AlertTriangle,
} from "lucide-react";

interface ComplianceProfile {
  profile_id: string;
  business_id: string;
  country_code: string;
  customer_type: string;
  legal_name: string;
  trade_name: string;
  tax_id: string;
  company_registration_number: string;
  physical_address: string;
  city: string;
  contact_email: string;
  contact_phone: string;
  state: string;
  tax_id_verified: boolean;
  company_reg_verified: boolean;
  address_verified: boolean;
  eligible_for_billing: boolean;
  rejection_reason: string | null;
  reviewer_id: string | null;
  review_notes: string | null;
  created_at: string | null;
  updated_at: string | null;
  verified_at: string | null;
  pack_ref: string | null;
}

export default function ComplianceReviewsPage() {
  const queryClient = useQueryClient();
  const [countryFilter, setCountryFilter] = useState("");
  const [selectedProfile, setSelectedProfile] = useState<ComplianceProfile | null>(null);
  const [reviewDecision, setReviewDecision] = useState<"approve" | "reject">("approve");
  const [reviewReason, setReviewReason] = useState("");
  const [showReviewDialog, setShowReviewDialog] = useState(false);

  const pendingQuery = useQuery({
    queryKey: ["platform", "compliance", "pending", countryFilter],
    queryFn: () => getPendingProfiles(countryFilter ? { country_code: countryFilter } : undefined),
    refetchInterval: 30_000,
  });

  const reviewMut = useMutation({
    mutationFn: (data: { profile_id: string; decision: "approve" | "reject"; reason: string }) =>
      reviewComplianceProfile({
        profile_id: data.profile_id,
        decision: data.decision,
        reviewer_id: localStorage.getItem("bos_actor_id") || "platform-admin",
        reason: data.reason,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform", "compliance", "pending"] });
      setShowReviewDialog(false);
      setSelectedProfile(null);
      setReviewReason("");
    },
  });

  const activateMut = useMutation({
    mutationFn: (profileId: string) => activateComplianceProfile({ profile_id: profileId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["platform", "compliance", "pending"] });
    },
  });

  const profiles: ComplianceProfile[] = pendingQuery.data?.data ?? [];
  const totalPending = pendingQuery.data?.total ?? 0;

  const submittedCount = profiles.filter((p) => p.state === "submitted").length;
  const underReviewCount = profiles.filter((p) => p.state === "under_review").length;

  // Get unique countries for filter
  const countries = [...new Set(profiles.map((p) => p.country_code))].sort();

  function handleReview(profile: ComplianceProfile, decision: "approve" | "reject") {
    setSelectedProfile(profile);
    setReviewDecision(decision);
    setShowReviewDialog(true);
  }

  function submitReview() {
    if (!selectedProfile) return;
    reviewMut.mutate({
      profile_id: selectedProfile.profile_id,
      decision: reviewDecision,
      reason: reviewReason,
    });
  }

  return (
    <div>
      <PageHeader
        title="Compliance Review Queue"
        description="Pending tenant compliance profiles awaiting review and verification"
        actions={
          <Button variant="outline" size="sm" onClick={() => pendingQuery.refetch()}>
            <RefreshCw className="mr-1 h-4 w-4" />
            Refresh
          </Button>
        }
      />

      {/* Queue Summary */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="border-l-4 border-l-orange-400 p-4">
          <div className="flex items-center gap-3">
            <Clock className="h-6 w-6 text-orange-500" />
            <div>
              <div className="text-2xl font-bold">{submittedCount}</div>
              <div className="text-sm text-neutral-500">Awaiting Review</div>
            </div>
          </div>
        </Card>
        <Card className="border-l-4 border-l-blue-400 p-4">
          <div className="flex items-center gap-3">
            <Eye className="h-6 w-6 text-blue-500" />
            <div>
              <div className="text-2xl font-bold">{underReviewCount}</div>
              <div className="text-sm text-neutral-500">Under Review</div>
            </div>
          </div>
        </Card>
        <Card className="border-l-4 border-l-purple-400 p-4">
          <div className="flex items-center gap-3">
            <ClipboardCheck className="h-6 w-6 text-bos-purple" />
            <div>
              <div className="text-2xl font-bold">{totalPending}</div>
              <div className="text-sm text-neutral-500">Total in Queue</div>
            </div>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="flex items-end gap-4 p-4">
          <div className="min-w-[200px]">
            <label className="mb-1 block text-xs font-medium text-neutral-500">Country</label>
            <Select value={countryFilter} onChange={(e) => setCountryFilter(e.target.value)}>
              <option value="">All Countries</option>
              {countries.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Profiles Table */}
      <Card>
        <CardHeader>
          <CardTitle>Pending Profiles ({profiles.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {pendingQuery.isLoading ? (
            <div className="py-8 text-center text-neutral-400">Loading...</div>
          ) : profiles.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-neutral-400">
              <CheckCircle className="h-10 w-10 text-green-400" />
              <div className="text-lg font-medium text-green-600">All caught up!</div>
              <div>No profiles pending review.</div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Business</TableHead>
                  <TableHead>Country</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Tax ID</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead>Submitted</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {profiles.map((p) => {
                  const daysSinceSubmit = p.created_at
                    ? Math.floor((Date.now() - new Date(p.created_at).getTime()) / 86_400_000)
                    : 0;
                  const isStuck = daysSinceSubmit > 7;

                  return (
                    <TableRow key={p.profile_id}>
                      <TableCell>
                        <div>
                          <div className="flex items-center gap-1 font-medium">
                            <Building className="h-3.5 w-3.5 text-neutral-400" />
                            {p.legal_name || p.trade_name || "Unnamed"}
                          </div>
                          {p.trade_name && p.legal_name !== p.trade_name && (
                            <div className="text-xs text-neutral-400">{p.trade_name}</div>
                          )}
                          <div className="text-xs text-neutral-400">{p.business_id.slice(0, 8)}...</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <MapPin className="h-3.5 w-3.5 text-neutral-400" />
                          <Badge variant="outline">{p.country_code}</Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={p.customer_type === "B2B" ? "outline" : "purple"}>
                          {p.customer_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs">
                        <div className="flex items-center gap-1">
                          {p.tax_id || <span className="text-neutral-300">--</span>}
                          {p.tax_id_verified && <CheckCircle className="h-3 w-3 text-green-500" />}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <StatusBadge status={p.state.toUpperCase()} label={p.state} />
                          {isStuck && (
                            <AlertTriangle className="h-3.5 w-3.5 text-orange-500" title={`Stuck: ${daysSinceSubmit} days`} />
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-neutral-400">
                        {p.created_at ? (
                          <div>
                            {new Date(p.created_at).toLocaleDateString()}
                            {isStuck && (
                              <div className="text-orange-500 font-medium">{daysSinceSubmit}d ago</div>
                            )}
                          </div>
                        ) : "--"}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="default"
                            size="sm"
                            onClick={() => handleReview(p, "approve")}
                          >
                            <CheckCircle className="mr-1 h-3 w-3" />
                            Approve
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleReview(p, "reject")}
                          >
                            <XCircle className="mr-1 h-3 w-3" />
                            Reject
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Review Dialog */}
      {showReviewDialog && selectedProfile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <Card className="w-full max-w-lg">
            <CardHeader>
              <CardTitle>
                {reviewDecision === "approve" ? "Approve" : "Reject"} Compliance Profile
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="rounded-md bg-neutral-50 p-3 dark:bg-neutral-900">
                  <div className="text-sm font-medium">{selectedProfile.legal_name}</div>
                  <div className="mt-1 text-xs text-neutral-500">
                    {selectedProfile.country_code} | {selectedProfile.customer_type} | Tax ID: {selectedProfile.tax_id || "N/A"}
                  </div>
                  <div className="mt-1 text-xs text-neutral-400">
                    {selectedProfile.physical_address}, {selectedProfile.city}
                  </div>
                  <div className="mt-1 text-xs text-neutral-400">
                    {selectedProfile.contact_email} | {selectedProfile.contact_phone}
                  </div>
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium">
                    {reviewDecision === "reject" ? "Rejection Reason" : "Review Notes"} *
                  </label>
                  <Textarea
                    placeholder={reviewDecision === "reject"
                      ? "Explain why this profile is being rejected..."
                      : "Optional review notes..."
                    }
                    value={reviewReason}
                    onChange={(e) => setReviewReason(e.target.value)}
                    rows={3}
                  />
                </div>

                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowReviewDialog(false);
                      setSelectedProfile(null);
                      setReviewReason("");
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant={reviewDecision === "reject" ? "destructive" : "default"}
                    onClick={submitReview}
                    disabled={reviewMut.isPending || (reviewDecision === "reject" && !reviewReason)}
                  >
                    {reviewMut.isPending ? "Processing..." : reviewDecision === "reject" ? "Reject Profile" : "Approve Profile"}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
