import { useQuery } from "@tanstack/react-query";
import { getRegions } from "@/lib/api/saas";
import { REGIONS as REGIONS_FALLBACK } from "@/lib/constants";

export type LiveRegion = {
  code: string;
  name: string;
  currency: string;
  status?: string;
  tax_name?: string;
  vat_rate?: number;
  digital_tax_rate?: number;
  b2b_reverse_charge?: boolean;
  registration_required?: boolean;
};

/**
 * Fetches registered regions from the backend.
 * Falls back to the hardcoded REGIONS constant while loading or on error,
 * so dropdowns are never empty.
 */
export function useRegions(opts?: { onlyActive?: boolean }) {
  const query = useQuery<{ data?: LiveRegion[]; regions?: LiveRegion[] }>({
    queryKey: ["saas", "regions"],
    queryFn: getRegions,
    staleTime: 5 * 60 * 1000, // cache 5 min — regions change rarely
  });

  const raw: LiveRegion[] =
    query.data?.data ?? query.data?.regions ?? [];

  const regions: LiveRegion[] =
    raw.length > 0
      ? opts?.onlyActive
        ? raw.filter((r) => !r.status || r.status === "ACTIVE" || r.status === "LAUNCHED")
        : raw
      : (REGIONS_FALLBACK as unknown as LiveRegion[]);

  return { regions, isLoading: query.isLoading, isError: query.isError };
}

/** Quick lookup: code → region object (from live data or fallback) */
export function useRegionMap() {
  const { regions } = useRegions();
  const map = Object.fromEntries(regions.map((r) => [r.code, r]));
  return map;
}
