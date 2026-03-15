"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { FormDialog } from "@/components/shared/form-dialog";
import { Button, Card, CardContent, Input, Label, Select, Textarea, Toast } from "@/components/ui";
import { getEngines, registerEngine } from "@/lib/api/saas";
import { Cog, Plus } from "lucide-react";

export default function EnginesPage() {
  const queryClient = useQueryClient();
  const [showRegister, setShowRegister] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const engines = useQuery({ queryKey: ["saas", "engines"], queryFn: getEngines });

  const registerMut = useMutation({
    mutationFn: registerEngine,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saas", "engines"] });
      setShowRegister(false);
      setToast({ message: "Engine registered successfully", variant: "success" });
    },
    onError: () => {
      setToast({ message: "Failed to register engine", variant: "error" });
    },
  });

  function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const data = new FormData(form);
    registerMut.mutate({
      engine_key: data.get("engine_key") as string,
      display_name: data.get("display_name") as string,
      category: data.get("category") as "FREE" | "PAID",
      description: data.get("description") as string,
    });
  }

  const engineList = engines.data?.data ?? [];

  return (
    <div>
      <PageHeader
        title="Engine Catalog"
        description="Engines zote za BOS platform. Ongeza engine mpya kwa catalog."
        actions={
          <Button onClick={() => setShowRegister(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Register Engine
          </Button>
        }
      />

      {engines.isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="animate-pulse p-5">
              <div className="h-4 w-24 rounded bg-neutral-200" />
              <div className="mt-2 h-3 w-40 rounded bg-neutral-200" />
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {engineList.map((engine: { engine_key: string; display_name: string; category: string; description?: string }) => (
            <Card key={engine.engine_key} className="transition-shadow hover:shadow-md">
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-bos-purple-light">
                      <Cog className="h-4 w-4 text-bos-purple" />
                    </div>
                    <div>
                      <p className="font-mono text-sm font-medium">{engine.engine_key}</p>
                      <p className="text-xs text-bos-silver-dark">{engine.display_name}</p>
                    </div>
                  </div>
                  <StatusBadge status={engine.category} />
                </div>
                {engine.description && (
                  <p className="mt-3 text-xs text-bos-silver-dark">{engine.description}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Register Engine Dialog */}
      <FormDialog
        open={showRegister}
        onClose={() => setShowRegister(false)}
        title="Register Engine"
        description="Ongeza engine mpya kwa BOS platform catalog"
        onSubmit={handleRegister}
        submitLabel="Register"
        loading={registerMut.isPending}
      >
        <div>
          <Label htmlFor="engine_key">Engine Key</Label>
          <Input id="engine_key" name="engine_key" placeholder="e.g. retail" required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="display_name">Display Name</Label>
          <Input id="display_name" name="display_name" placeholder="e.g. Retail (POS/Shop)" required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="category">Category</Label>
          <Select id="category" name="category" className="mt-1">
            <option value="PAID">PAID</option>
            <option value="FREE">FREE</option>
          </Select>
        </div>
        <div>
          <Label htmlFor="description">Description</Label>
          <Textarea id="description" name="description" placeholder="Short description..." className="mt-1" />
        </div>
      </FormDialog>

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}
