"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { FlaskConical, Menu, Store } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { MerchantNav, merchantTitleFor } from "@/components/merchant/nav";

export default function MerchantLayout({ children }: LayoutProps<"/merchant">) {
  const pathname = usePathname();
  const { state } = useCommerce();
  const [navOpen, setNavOpen] = useState(false);

  const title = merchantTitleFor(pathname);

  const brand = (
    <div className="flex h-14 items-center gap-2 border-b px-5">
      <Store className="size-4 text-primary" aria-hidden />
      <div className="leading-tight">
        <p className="text-sm font-semibold">Commerce Gateway</p>
        <p className="text-xs text-muted-foreground">Merchant console</p>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-svh">
      {/* Desktop sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col border-r bg-card md:flex">
        {brand}
        <div className="py-4">
          <MerchantNav />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-10 flex h-14 items-center gap-2 border-b bg-card px-4 md:px-6">
          <Sheet open={navOpen} onOpenChange={setNavOpen}>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden"
                aria-label="Open navigation"
              >
                <Menu aria-hidden />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-60 p-0">
              <SheetHeader className="sr-only">
                <SheetTitle>Merchant navigation</SheetTitle>
              </SheetHeader>
              {brand}
              <div className="py-4">
                <MerchantNav onNavigate={() => setNavOpen(false)} />
              </div>
            </SheetContent>
          </Sheet>

          <h1 className="text-sm font-semibold md:text-base">{title}</h1>

          <div className="ml-auto flex items-center gap-3">
            <Badge variant="warning">
              <FlaskConical aria-hidden />
              Test Mode
            </Badge>
            <div className="hidden items-center gap-2 text-sm sm:flex">
              <Store className="size-4 text-muted-foreground" aria-hidden />
              <span className="font-medium">{state.merchant.name}</span>
            </div>
          </div>
        </header>

        <main className="flex-1">
          <div className="mx-auto w-full max-w-6xl space-y-6 p-4 md:p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
