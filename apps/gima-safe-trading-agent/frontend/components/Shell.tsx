import Link from "next/link";
import type { ReactNode } from "react";
import { BarChart3, BookOpen, Gauge, ListChecks, Settings, ShieldAlert, TrendingUp } from "lucide-react";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/watchlist", label: "Watchlist", icon: ListChecks },
  { href: "/signals", label: "Signals", icon: TrendingUp },
  { href: "/backtests", label: "Backtests", icon: BarChart3 },
  { href: "/orders", label: "Orders", icon: ShieldAlert },
  { href: "/journal", label: "Journal", icon: BookOpen },
  { href: "/settings/risk", label: "Risk", icon: Settings }
];

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-black/10 bg-white/90">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-normal">Gima Safe Trading Agent</h1>
            <p className="text-sm font-medium text-red-700">Paper trading only. Trading involves risk.</p>
          </div>
          <nav className="flex flex-wrap gap-2">
            {links.map((item) => {
              const Icon = item.icon;
              return (
                <Link className="inline-flex items-center gap-2 rounded-md border border-black/10 bg-white px-3 py-2 text-sm hover:bg-mint" href={item.href} key={item.href}>
                  <Icon size={16} aria-hidden />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  );
}
