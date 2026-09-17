import type { Evidence } from "@/src/types/api";

export function StatusRow({ label, evidence }: { label: string; evidence?: Evidence | null }) {
  const value = evidence?.value ?? "?";
  const marker = evidence ? (evidence.status === "hypothesis" ? "?" : "✓") : "?";
  return (
    <div className="grid grid-cols-[7.5rem_1fr_2rem] items-center gap-3 border-b border-line py-2 text-sm">
      <span className="text-ink/60">{label}</span>
      <span className={evidence ? "font-medium" : "text-ink/45"}>{value}</span>
      <span className={evidence ? "text-signal" : "text-caution"}>{marker}</span>
    </div>
  );
}
