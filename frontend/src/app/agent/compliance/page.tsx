"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Button, Card, CardContent, CardHeader, CardTitle, Input, Label, Select, Toast, Badge,
} from "@/components/ui";
import { getComplianceDocs, submitComplianceDoc } from "@/lib/api/agents";
import { COMPLIANCE_DOC_TYPES } from "@/lib/constants";
import { ShieldCheck, Upload } from "lucide-react";

export default function AgentCompliancePage() {
  const qc = useQueryClient();
  const [showSubmit, setShowSubmit] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const docs = useQuery({ queryKey: ["agent", "compliance"], queryFn: getComplianceDocs });

  const submitMut = useMutation({
    mutationFn: submitComplianceDoc,
    onSuccess: () => { setShowSubmit(false); qc.invalidateQueries({ queryKey: ["agent", "compliance"] }); setToast({ message: "Document submitted for review", variant: "success" }); },
    onError: () => setToast({ message: "Failed to submit document", variant: "error" }),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const d = new FormData(e.target as HTMLFormElement);
    submitMut.mutate({
      doc_type: d.get("doc_type") as string,
      title: d.get("title") as string,
      summary: d.get("summary") as string,
      file_url: (d.get("file_url") as string) || undefined,
    });
  }

  const docList = docs.data?.data ?? [];

  return (
    <div>
      <PageHeader
        title="Compliance Documents"
        description="Submit regulatory and compliance documents for your territory"
        actions={
          <Button onClick={() => setShowSubmit(true)} className="gap-2">
            <Upload className="h-4 w-4" />
            Submit Document
          </Button>
        }
      />

      <div className="mb-6 rounded-lg border border-bos-purple/20 bg-bos-purple/5 p-4">
        <h3 className="mb-1 text-sm font-semibold text-bos-purple">Regional Agent Responsibility</h3>
        <p className="text-xs text-bos-silver-dark">
          As a regional agent, you are responsible for understanding and documenting local tax rules,
          business regulations, data residency requirements, and payment processor restrictions in your territory.
          Submit relevant documents here for platform review and integration.
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-bos-purple" />
            <CardTitle className="text-base">Submitted Documents</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-bos-silver/20 bg-bos-silver-light dark:bg-neutral-900">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Title</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Summary</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-bos-silver-dark">Submitted</th>
                </tr>
              </thead>
              <tbody>
                {docList.length === 0 && (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-bos-silver-dark">
                    <ShieldCheck className="mx-auto mb-2 h-5 w-5" />
                    No compliance documents submitted yet.
                  </td></tr>
                )}
                {docList.map((d: {
                  id: string; doc_type: string; title: string;
                  summary: string; status: string; submitted_at: string;
                }) => (
                  <tr key={d.id} className="border-b border-bos-silver/10 hover:bg-bos-silver-light/50 dark:hover:bg-neutral-900/50">
                    <td className="px-4 py-3">
                      <Badge variant="outline">
                        {COMPLIANCE_DOC_TYPES.find((t) => t.value === d.doc_type)?.label ?? d.doc_type}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 font-medium">{d.title}</td>
                    <td className="px-4 py-3 text-bos-silver-dark max-w-xs truncate">{d.summary}</td>
                    <td className="px-4 py-3"><StatusBadge status={d.status} /></td>
                    <td className="px-4 py-3 text-bos-silver-dark">{d.submitted_at?.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <FormDialog
        open={showSubmit}
        onClose={() => setShowSubmit(false)}
        title="Submit Compliance Document"
        description="Upload regulatory information relevant to your territory."
        onSubmit={handleSubmit}
        submitLabel="Submit"
        loading={submitMut.isPending}
      >
        <div>
          <Label htmlFor="cd_type">Document Type</Label>
          <Select id="cd_type" name="doc_type" required className="mt-1">
            {COMPLIANCE_DOC_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </Select>
        </div>
        <div>
          <Label htmlFor="cd_title">Title</Label>
          <Input id="cd_title" name="title" required className="mt-1" placeholder="e.g. Kenya VAT Rules 2026" />
        </div>
        <div>
          <Label htmlFor="cd_summary">Summary</Label>
          <Input id="cd_summary" name="summary" required className="mt-1" placeholder="Brief summary of the document content" />
        </div>
        <div>
          <Label htmlFor="cd_url">File URL (optional)</Label>
          <Input id="cd_url" name="file_url" className="mt-1" placeholder="https://..." />
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
