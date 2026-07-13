export function StatusBadge({ value }: { value: string }) {
  const normalized = value.toUpperCase();
  const tone =
    normalized.includes("BLOCK") || normalized.includes("REJECT") || normalized.includes("CANCEL")
      ? "bg-red-100 text-red-800"
      : normalized.includes("PENDING") || normalized.includes("WAIT")
        ? "bg-amber-100 text-amber-900"
        : "bg-green-100 text-green-800";
  return <span className={`rounded px-2 py-1 text-xs font-medium ${tone}`}>{value}</span>;
}
