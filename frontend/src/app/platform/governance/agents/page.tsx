"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  Select,
  Input,
} from "@/components/ui";
import { getGovernanceAgents } from "@/lib/api/platform";
import {
  Shield,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  UserCheck,
} from "lucide-react";

const STATUS_CONFIG: Record<string, { color: string; icon: typeof CheckCircle }> = {
  ACTIVE: { color: "bg-green-100 text-green-700", icon: CheckCircle },
  SUSPENDED: { color: "bg-yellow-100 text-yellow-700", icon: Clock },
  REVOKED: { color: "bg-red-100 text-red-700", icon: XCircle },
  PENDING: { color: "bg-blue-100 text-blue-700", icon: Clock },
};

export default function GovernanceAgentsPage() {
  const [regionCode, setRegionCode] = useState("KE");

  const agentsQuery = useQuery({
    queryKey: ["platform", "governance", "agents", regionCode],
    queryFn: () => getGovernanceAgents(regionCode),
    enabled: !!regionCode,
  });

  const agents = agentsQuery.data?.data ?? [];

  return (
    <div>
      <PageHeader
        title="Region Agents — Governance"
        description="Two-level governance: Main Admin delegates compliance execution to Region/License Agents"
        actions={
          <Button variant="outline" size="sm" onClick={() => agentsQuery.refetch()}>
            <RefreshCw className="mr-1 h-4 w-4" />
            Refresh
          </Button>
        }
      />

      {/* Governance Model Explanation */}
      <Card className="mb-6 border-l-4 border-l-bos-purple">
        <CardContent className="p-5">
          <div className="flex gap-4">
            <Shield className="h-8 w-8 text-bos-purple flex-shrink-0" />
            <div>
              <h3 className="font-bold text-bos-purple">Two-Level Governance Model</h3>
              <div className="mt-1 text-sm text-neutral-600 space-y-1">
                <p><strong>Main Admin:</strong> Platform doctrine, architecture, security, pricing, compliance pack publishing</p>
                <p><strong>Region Agent:</strong> Local compliance execution, tax filing, local payments, tenant onboarding, L1 support</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Region Selector */}
      <Card className="mb-6">
        <CardContent className="flex items-end gap-4 p-4">
          <div className="min-w-[200px]">
            <label className="mb-1 block text-xs font-medium text-neutral-500">Region Code</label>
            <Input
              value={regionCode}
              onChange={(e) => setRegionCode(e.target.value.toUpperCase())}
              placeholder="e.g. KE, TZ, UG"
              className="uppercase"
            />
          </div>
          <Button size="sm" onClick={() => agentsQuery.refetch()}>
            Search
          </Button>
        </CardContent>
      </Card>

      {/* Main Admin Permissions */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-bos-purple" />
            Main Admin Exclusive Permissions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {[
              "DEFINE_DOCTRINE", "SET_PRICING_POLICY", "MANAGE_ENGINES",
              "PUBLISH_COMPLIANCE_PACK", "SET_SECURITY_POLICY", "MANAGE_PLATFORM_USERS",
              "VIEW_ALL_REGIONS", "KILL_SWITCH", "APPROVE_REGION_AGENT", "SET_COMMISSION_POLICY",
            ].map((perm) => (
              <Badge key={perm} variant="outline" className="text-xs">
                {perm.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Region Agents Table */}
      <Card>
        <CardHeader>
          <CardTitle>
            Region Agents for {regionCode || "—"} ({agents.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {agentsQuery.isLoading ? (
            <div className="py-8 text-center text-neutral-400">Loading...</div>
          ) : !regionCode ? (
            <div className="py-12 text-center text-neutral-400">
              Enter a region code to view agents.
            </div>
          ) : agents.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-neutral-400">
              <UserCheck className="h-10 w-10 text-neutral-300" />
              <div>No governance agents found for region {regionCode}.</div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent ID</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Can File Taxes</TableHead>
                  <TableHead>Max Tenants</TableHead>
                  <TableHead>Permissions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agents.map((agent: {
                  reseller_id: string;
                  governance_role: string;
                  governance_status: string;
                  can_file_taxes: boolean;
                  max_tenants: number;
                  permissions: { permission_code: string; granted_at: string }[];
                }) => {
                  const cfg = STATUS_CONFIG[agent.governance_status] || STATUS_CONFIG.PENDING;
                  const StatusIcon = cfg.icon;
                  return (
                    <TableRow key={agent.reseller_id}>
                      <TableCell className="font-mono text-xs">
                        {agent.reseller_id.slice(0, 12)}...
                      </TableCell>
                      <TableCell>
                        <Badge variant={agent.governance_role === "LICENSE_AGENT" ? "purple" : "outline"}>
                          {agent.governance_role.replace(/_/g, " ")}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1.5">
                          <StatusIcon className={`h-4 w-4 ${agent.governance_status === "ACTIVE" ? "text-green-500" : "text-neutral-400"}`} />
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${cfg.color}`}>
                            {agent.governance_status}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        {agent.can_file_taxes ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-neutral-300" />
                        )}
                      </TableCell>
                      <TableCell className="font-medium">
                        {agent.max_tenants || "Unlimited"}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {agent.permissions.slice(0, 3).map((p) => (
                            <Badge key={p.permission_code} variant="outline" className="text-[10px]">
                              {p.permission_code.replace(/_/g, " ")}
                            </Badge>
                          ))}
                          {agent.permissions.length > 3 && (
                            <Badge variant="outline" className="text-[10px]">
                              +{agent.permissions.length - 3} more
                            </Badge>
                          )}
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

      {/* Region Agent Permissions Reference */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-neutral-500" />
            Delegatable Permissions (Region Agent)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {[
              { code: "ONBOARD_TENANTS", desc: "Register new tenants in their region" },
              { code: "REVIEW_COMPLIANCE_PROFILES", desc: "Approve/reject tenant compliance" },
              { code: "FILE_LOCAL_TAXES", desc: "File taxes with local authority" },
              { code: "MANAGE_LOCAL_PAYMENTS", desc: "Configure local payment channels" },
              { code: "PROVIDE_L1_SUPPORT", desc: "First-line tenant support" },
              { code: "VIEW_REGION_DATA", desc: "Regional metrics and reports" },
              { code: "MANAGE_TERRITORY", desc: "Assign sub-territories" },
              { code: "SUBMIT_COMPLIANCE_EVIDENCE", desc: "Upload tax filings, registration docs" },
              { code: "ESCALATE_TO_MAIN_ADMIN", desc: "Escalate beyond agent authority" },
              { code: "CONFIGURE_LOCAL_SETTINGS", desc: "Language, timezone, local config" },
            ].map((perm) => (
              <div key={perm.code} className="flex items-start gap-2 rounded-md bg-neutral-50 p-2 dark:bg-neutral-900">
                <CheckCircle className="mt-0.5 h-3.5 w-3.5 text-green-500 flex-shrink-0" />
                <div>
                  <div className="text-xs font-semibold">{perm.code.replace(/_/g, " ")}</div>
                  <div className="text-[10px] text-neutral-500">{perm.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
