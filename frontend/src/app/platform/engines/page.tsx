"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button, Card, CardContent, Toast, Badge } from "@/components/ui";
import { getEngines, registerEngine } from "@/lib/api/saas";
import { BACKEND_ENGINES } from "@/lib/constants";
import { Cog, Plus, Check, CircleDashed } from "lucide-react";

export default function EnginesPage() {
  const queryClient = useQueryClient();
  const [registerKey, setRegisterKey] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(null);

  const engines = useQuery({ queryKey: ["saas", "engines"], queryFn: getEngines });

  // Set of engine_keys already registered in backend SaaS catalog
  const registeredKeys = new Set(
    (engines.data?.data ?? []).map((e: { engine_key: string }) => e.engine_key)
  );

  const registerMut = useMutation({
    mutationFn: registerEngine,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saas", "engines"] });
      setRegisterKey(null);
      setToast({ message: "Engine registered successfully", variant: "success" });
    },
    onError: () => {
      setRegisterKey(null);
      setToast({ message: "Failed to register engine", variant: "error" });
    },
  });

  function handleRegister() {
    if (!registerKey) return;
    const eng = BACKEND_ENGINES.find((e) => e.key === registerKey);
    if (!eng) return;
    registerMut.mutate({
      engine_key: eng.key,
      display_name: eng.displayName,
      category: eng.category,
      description: eng.description,
    });
  }

  function handleRegisterAll() {
    const unregistered = BACKEND_ENGINES.filter((e) => !registeredKeys.has(e.key));
    if (unregistered.length === 0) return;
    // Register one by one sequentially
    const chain = unregistered.reduce(
      (p, eng) =>
        p.then(() =>
          registerEngine({
            engine_key: eng.key,
            display_name: eng.displayName,
            category: eng.category,
            description: eng.description,
          })
        ),
      Promise.resolve({} as ReturnType<typeof registerEngine> extends Promise<infer T> ? T : never)
    );
    chain.then(() => {
      queryClient.invalidateQueries({ queryKey: ["saas", "engines"] });
      setToast({ message: `${unregistered.length} engines registered`, variant: "success" });
    }).catch(() => {
      queryClient.invalidateQueries({ queryKey: ["saas", "engines"] });
      setToast({ message: "Some engines failed to register", variant: "error" });
    });
  }

  const freeEngines = BACKEND_ENGINES.filter((e) => e.category === "FREE");
  const paidEngines = BACKEND_ENGINES.filter((e) => e.category === "PAID");
  const unregisteredCount = BACKEND_ENGINES.filter((e) => !registeredKeys.has(e.key)).length;

  return (
    <div>
      <PageHeader
        title="Engine Catalog"
        description="All BOS platform engines — connected to the backend codebase"
        actions={
          unregisteredCount > 0 ? (
            <Button onClick={handleRegisterAll} className="gap-2">
              <Plus className="h-4 w-4" />
              Register All ({unregisteredCount})
            </Button>
          ) : (
            <Badge variant="success" className="px-3 py-1.5">All engines registered</Badge>
          )
        }
      />

      {/* FREE Engines */}
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-bos-silver-dark">
        Free Engines — Every tenant gets these
      </h2>
      <div className="mb-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {freeEngines.map((eng) => (
          <EngineCard
            key={eng.key}
            engineKey={eng.key}
            displayName={eng.displayName}
            description={eng.description}
            category="FREE"
            registered={registeredKeys.has(eng.key)}
            onRegister={() => setRegisterKey(eng.key)}
          />
        ))}
      </div>

      {/* PAID Engines */}
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-bos-silver-dark">
        Paid Engines — Available through combo/plan subscriptions
      </h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {paidEngines.map((eng) => (
          <EngineCard
            key={eng.key}
            engineKey={eng.key}
            displayName={eng.displayName}
            description={eng.description}
            category="PAID"
            registered={registeredKeys.has(eng.key)}
            onRegister={() => setRegisterKey(eng.key)}
          />
        ))}
      </div>

      {/* Register Confirmation */}
      <ConfirmDialog
        open={!!registerKey}
        onClose={() => setRegisterKey(null)}
        onConfirm={handleRegister}
        title="Register Engine"
        description={`Register "${BACKEND_ENGINES.find((e) => e.key === registerKey)?.displayName ?? registerKey}" in the SaaS engine catalog?`}
        confirmLabel="Register"
        loading={registerMut.isPending}
      />

      {toast && <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />}
    </div>
  );
}

function EngineCard({
  engineKey,
  displayName,
  description,
  category,
  registered,
  onRegister,
}: {
  engineKey: string;
  displayName: string;
  description: string;
  category: "FREE" | "PAID";
  registered: boolean;
  onRegister: () => void;
}) {
  return (
    <Card className={`transition-shadow hover:shadow-md ${registered ? "" : "border-dashed"}`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${
              registered ? "bg-bos-purple-light" : "bg-neutral-100 dark:bg-neutral-800"
            }`}>
              <Cog className={`h-4 w-4 ${registered ? "text-bos-purple" : "text-bos-silver-dark"}`} />
            </div>
            <div>
              <p className="text-sm font-semibold">{displayName}</p>
              <code className="text-[10px] text-bos-silver-dark">{engineKey}</code>
            </div>
          </div>
          <StatusBadge status={category} />
        </div>
        <p className="mt-2 text-xs text-bos-silver-dark leading-relaxed">{description}</p>
        <div className="mt-3">
          {registered ? (
            <div className="flex items-center gap-1.5 text-xs font-medium text-green-600">
              <Check className="h-3.5 w-3.5" />
              Registered
            </div>
          ) : (
            <button
              onClick={onRegister}
              className="flex items-center gap-1.5 text-xs font-medium text-bos-purple hover:text-bos-purple-dark transition-colors"
            >
              <CircleDashed className="h-3.5 w-3.5" />
              Click to register
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
