export function money(value: number | string | null | undefined): string {
  const numeric = Number(value ?? 0);
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(Number.isFinite(numeric) ? numeric : 0);
}

export function percent(value: number | null | undefined): string {
  return `${Number(value ?? 0).toFixed(2)}%`;
}

export function confidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function shortDate(value: string): string {
  return new Date(value).toLocaleString();
}

export function csvEscape(value: unknown): string {
  const text = String(value ?? "");
  return `"${text.replaceAll('"', '""')}"`;
}
