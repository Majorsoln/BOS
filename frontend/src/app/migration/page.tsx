"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { FormDialog } from "@/components/shared/form-dialog";
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
  Badge, Button, Input, Label, Select, Toast, Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui";
import { EmptyState } from "@/components/shared/empty-state";
import api from "@/lib/api/client";

const SUPPORTED_SOURCES = [
  "quickbooks", "xero", "sage", "odoo", "erpnext",
  "tally", "wave", "zoho_books", "freshbooks",
  "csv_generic", "json_generic", "excel_generic",
];

const SOURCE_LABELS: Record<string, string> = {
  quickbooks: "QuickBooks", xero: "Xero", sage: "Sage", odoo: "Odoo",
  erpnext: "ERPNext", tally: "Tally", wave: "Wave", zoho_books: "Zoho Books",
  freshbooks: "FreshBooks", csv_generic: "CSV", json_generic: "JSON", excel_generic: "Excel",
};

const ENTITY_TYPES = [
  { type: "CUSTOMER", label: "Customers", description: "Import customer profiles with names, contacts, addresses" },
  { type: "SUPPLIER", label: "Suppliers", description: "Import supplier records for procurement" },
  { type: "PRODUCT", label: "Products", description: "Import product catalog with SKUs and pricing" },
  { type: "OPENING_BALANCE", label: "Opening Balances", description: "Import account opening balances for accounting" },
  { type: "TRANSACTION", label: "Transactions", description: "Import historical transactions for reporting continuity" },
];

interface MigrationJob {
  job_id: string;
  source_system: string;
  entity_type: string;
  status: string;
  total_rows?: number;
  success_count?: number;
  error_count?: number;
  created_at?: string;
}

interface ImportResult {
  external_id: string;
  status: string;
  bos_id?: string;
  error?: string;
}

type WizardStep = "select" | "upload" | "results";

export default function MigrationPage() {
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  // Wizard state
  const [step, setStep] = useState<WizardStep>("select");
  const [sourceSystem, setSourceSystem] = useState("");
  const [entityType, setEntityType] = useState("");
  const [currentJob, setCurrentJob] = useState<MigrationJob | null>(null);
  const [creating, setCreating] = useState(false);

  // Upload state
  const [jsonInput, setJsonInput] = useState("");
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState<ImportResult[]>([]);

  // Jobs list
  const [jobs, setJobs] = useState<MigrationJob[]>([]);
  const [showJobs, setShowJobs] = useState(false);
  const [loadingJobs, setLoadingJobs] = useState(false);

  async function handleCreateJob(e: React.FormEvent) {
    e.preventDefault();
    if (!sourceSystem || !entityType) return;
    setCreating(true);
    try {
      const { data } = await api.post("/admin/migration/create-job", {
        source_system: sourceSystem,
        entity_type: entityType,
      });
      setCurrentJob(data.job || data);
      setStep("upload");
      setToast({ message: "Migration job created", variant: "success" });
    } catch {
      setToast({ message: "Failed to create migration job", variant: "error" });
    } finally {
      setCreating(false);
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!currentJob || !jsonInput.trim()) return;
    setUploading(true);
    try {
      let rows: Record<string, unknown>[];
      try {
        rows = JSON.parse(jsonInput);
        if (!Array.isArray(rows)) rows = [rows];
      } catch {
        setToast({ message: "Invalid JSON. Paste a JSON array of records.", variant: "error" });
        setUploading(false);
        return;
      }

      const { data } = await api.post("/admin/migration/upload", {
        job_id: currentJob.job_id,
        rows,
      });
      setResults(data.results || []);
      setStep("results");
      setToast({ message: `Batch uploaded: ${data.success_count || 0} succeeded, ${data.error_count || 0} failed`, variant: "success" });
    } catch {
      setToast({ message: "Failed to upload batch", variant: "error" });
    } finally {
      setUploading(false);
    }
  }

  async function handleComplete() {
    if (!currentJob) return;
    try {
      await api.post("/admin/migration/complete", { job_id: currentJob.job_id });
      setToast({ message: "Migration job completed", variant: "success" });
      resetWizard();
    } catch {
      setToast({ message: "Failed to complete job", variant: "error" });
    }
  }

  async function loadJobs() {
    setLoadingJobs(true);
    setShowJobs(true);
    try {
      const { data } = await api.get("/admin/migration/jobs");
      setJobs(data.jobs || []);
    } catch {
      setToast({ message: "Failed to load jobs", variant: "error" });
    } finally {
      setLoadingJobs(false);
    }
  }

  function resetWizard() {
    setStep("select");
    setSourceSystem("");
    setEntityType("");
    setCurrentJob(null);
    setJsonInput("");
    setResults([]);
  }

  return (
    <AppShell>
      <PageHeader
        title="Data Migration"
        description="Import data from other ERP systems into BOS (Hamisha Data)"
        actions={
          <Button variant="outline" size="sm" onClick={loadJobs}>
            View Past Jobs
          </Button>
        }
      />

      {/* Step Indicator */}
      <div className="mb-6 flex items-center gap-2">
        {(["select", "upload", "results"] as const).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            {i > 0 && <div className="h-px w-8 bg-bos-silver/40" />}
            <div className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold ${
              step === s ? "bg-bos-purple text-white" : "bg-neutral-100 text-neutral-400 dark:bg-neutral-800"
            }`}>
              {i + 1}
            </div>
            <span className={`text-sm ${step === s ? "font-semibold" : "text-neutral-400"}`}>
              {s === "select" ? "Configure" : s === "upload" ? "Upload Data" : "Results"}
            </span>
          </div>
        ))}
      </div>

      {/* Step 1: Select source & entity */}
      {step === "select" && (
        <Card>
          <CardHeader>
            <CardTitle>New Migration Job</CardTitle>
            <CardDescription>Select the source system and data type to import</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateJob} className="space-y-4">
              <div>
                <Label htmlFor="source">Source System</Label>
                <Select id="source" value={sourceSystem} onChange={(e) => setSourceSystem(e.target.value)} required>
                  <option value="">-- Select source --</option>
                  {SUPPORTED_SOURCES.map((s) => (
                    <option key={s} value={s}>{SOURCE_LABELS[s] || s}</option>
                  ))}
                </Select>
              </div>
              <div>
                <Label htmlFor="entity">Entity Type</Label>
                <Select id="entity" value={entityType} onChange={(e) => setEntityType(e.target.value)} required>
                  <option value="">-- Select entity type --</option>
                  {ENTITY_TYPES.map((et) => (
                    <option key={et.type} value={et.type}>{et.label} — {et.description}</option>
                  ))}
                </Select>
              </div>
              <Button type="submit" disabled={creating}>
                {creating ? "Creating..." : "Create Job & Continue"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Upload data */}
      {step === "upload" && currentJob && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Data</CardTitle>
            <CardDescription>
              Job: <Badge variant="outline" className="ml-1">{currentJob.job_id?.slice(0, 12)}</Badge>
              {" | "}Source: <Badge variant="secondary">{SOURCE_LABELS[currentJob.source_system] || currentJob.source_system}</Badge>
              {" | "}Entity: <Badge variant="purple">{currentJob.entity_type}</Badge>
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <Label htmlFor="jsonData">Data (JSON array)</Label>
                <textarea
                  id="jsonData"
                  value={jsonInput}
                  onChange={(e) => setJsonInput(e.target.value)}
                  rows={12}
                  placeholder={getPlaceholder(entityType)}
                  className="flex w-full rounded-md border border-bos-silver/60 bg-white px-3 py-2 font-mono text-sm placeholder:text-neutral-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bos-purple/40 dark:border-bos-silver dark:bg-neutral-950"
                  required
                />
              </div>
              <div className="flex gap-3">
                <Button type="submit" disabled={uploading}>
                  {uploading ? "Uploading..." : "Upload Batch"}
                </Button>
                <Button type="button" variant="outline" onClick={resetWizard}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Results */}
      {step === "results" && (
        <Card>
          <CardHeader>
            <CardTitle>Import Results</CardTitle>
            <CardDescription>
              {results.filter((r) => r.status === "ok" || r.status === "created").length} succeeded,{" "}
              {results.filter((r) => r.status === "error" || r.status === "skipped").length} failed/skipped
            </CardDescription>
          </CardHeader>
          <CardContent>
            {results.length === 0 ? (
              <EmptyState title="No results" />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>External ID</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>BOS ID</TableHead>
                    <TableHead>Error</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((r, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-sm">{r.external_id}</TableCell>
                      <TableCell>
                        <Badge variant={r.status === "ok" || r.status === "created" ? "success" : "destructive"}>
                          {r.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{r.bos_id || "\u2014"}</TableCell>
                      <TableCell className="text-sm text-red-600">{r.error || ""}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}

            <div className="mt-6 flex gap-3">
              <Button onClick={() => { setStep("upload"); setResults([]); setJsonInput(""); }}>
                Upload More
              </Button>
              <Button variant="outline" onClick={handleComplete}>
                Mark Job Complete
              </Button>
              <Button variant="ghost" onClick={resetWizard}>
                New Job
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Past Jobs */}
      {showJobs && (
        <Card className="mt-6">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Past Migration Jobs</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setShowJobs(false)}>Close</Button>
          </CardHeader>
          <CardContent>
            {loadingJobs ? (
              <p className="text-sm text-neutral-400">Loading...</p>
            ) : jobs.length === 0 ? (
              <EmptyState title="No migration jobs found" />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Job ID</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Entity</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Rows</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map((j) => (
                    <TableRow key={j.job_id}>
                      <TableCell className="font-mono text-xs">{j.job_id?.slice(0, 12)}...</TableCell>
                      <TableCell>{SOURCE_LABELS[j.source_system] || j.source_system}</TableCell>
                      <TableCell><Badge variant="outline">{j.entity_type}</Badge></TableCell>
                      <TableCell>
                        <Badge variant={j.status === "COMPLETED" ? "success" : j.status === "CANCELLED" ? "destructive" : "warning"}>
                          {j.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{j.total_rows ?? "\u2014"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {toast && (
        <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />
      )}
    </AppShell>
  );
}

function getPlaceholder(entityType: string): string {
  switch (entityType) {
    case "CUSTOMER":
      return `[\n  {\n    "external_id": "CUST-001",\n    "display_name": "John Doe",\n    "phone": "+254712345678",\n    "email": "john@example.com"\n  }\n]`;
    case "SUPPLIER":
      return `[\n  {\n    "external_id": "SUP-001",\n    "name": "Acme Supplies Ltd",\n    "phone": "+254700000000"\n  }\n]`;
    case "PRODUCT":
      return `[\n  {\n    "external_id": "PROD-001",\n    "name": "Widget A",\n    "sku": "WA-001",\n    "unit_price": 1500\n  }\n]`;
    case "OPENING_BALANCE":
      return `[\n  {\n    "external_id": "OB-001",\n    "account_code": "1000",\n    "balance": 500000\n  }\n]`;
    case "TRANSACTION":
      return `[\n  {\n    "external_id": "TXN-001",\n    "transaction_type": "SALE",\n    "total_amount": 25000,\n    "transaction_date": "2024-01-15"\n  }\n]`;
    default:
      return `[\n  { "external_id": "ID-001", ... }\n]`;
  }
}
