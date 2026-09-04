"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Inbox,
  LayoutDashboard,
  Package,
  ReceiptText,
  ScrollText,
  Settings,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { cn } from "@/lib/utils";

export const merchantNavItems = [
  { href: "/merchant", label: "Overview", icon: LayoutDashboard },
  { href: "/merchant/products", label: "Products", icon: Package },
  { href: "/merchant/ai-catalog", label: "AI Assistant", icon: Sparkles },
  { href: "/merchant/policy", label: "Policy", icon: ShieldCheck },
  { href: "/merchant/review", label: "Review Queue", icon: Inbox },
  { href: "/merchant/transactions", label: "Transactions", icon: ReceiptText },
  { href: "/merchant/audit", label: "Audit", icon: ScrollText },
  { href: "/merchant/settings", label: "Settings", icon: Settings },
] as const;

export function isNavActive(pathname: string, href: string): boolean {
  if (href === "/merchant") return pathname === href;
  return pathname === href || pathname.startsWith(href + "/");
}

export function merchantTitleFor(pathname: string): string {
  const item = merchantNavItems.find((i) => isNavActive(pathname, i.href));
  return item?.label ?? "Merchant";
}

export function MerchantNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Merchant sections" className="flex flex-col gap-1 px-3">
      {merchantNavItems.map((item) => {
        const active = isNavActive(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              active && "bg-primary/10 text-primary hover:bg-primary/10 hover:text-primary"
            )}
          >
            <item.icon className="size-4 shrink-0" aria-hidden />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
