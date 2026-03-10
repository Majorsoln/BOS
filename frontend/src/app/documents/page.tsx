"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, Table, TableBody, TableCell, TableHead, TableHeader, TableRow, Badge, Button } from "@/components/ui";
import { EmptyState } from "@/components/shared/empty-state";
import { listDocuments, getDocumentHtml } from "@/lib/api/admin";
import { formatDateTime } from "@/lib/utils";
import type { IssuedDocument } from "@/types/api";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<IssuedDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    listDocuments()
      .then((res) => setDocuments(res.documents || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handlePreview(docId: string) {
    try {
      const res = await getDocumentHtml(docId);
      setPreview(res.html || res.content || JSON.stringify(res, null, 2));
    } catch {
      alert("Failed to render document");
    }
  }

  const docTypeColor = (type: string): "default" | "secondary" | "success" | "outline" => {
    if (type.includes("RECEIPT")) return "success";
    if (type.includes("INVOICE")) return "default";
    if (type.includes("QUOTE")) return "secondary";
    return "outline";
  };

  return (
    <AppShell>
      <PageHeader title="Documents" description="All issued documents across engines" />

      {preview && (
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-medium">Document Preview</span>
              <Button variant="ghost" size="sm" onClick={() => setPreview(null)}>Close</Button>
            </div>
            <div
              className="rounded border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900"
              dangerouslySetInnerHTML={{ __html: preview }}
            />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p className="text-sm text-neutral-400">Loading...</p>
          ) : documents.length === 0 ? (
            <EmptyState title="No documents issued yet" description="Documents are auto-generated when business events fire (sales, bills, invoices, etc.)" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Number</TableHead>
                  <TableHead>Issued At</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((d) => (
                  <TableRow key={d.document_id}>
                    <TableCell>
                      <Badge variant={docTypeColor(d.document_type)}>{d.document_type}</Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{d.document_number || "—"}</TableCell>
                    <TableCell>{formatDateTime(d.issued_at)}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="outline" size="sm" onClick={() => handlePreview(d.document_id)}>
                        Preview
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
