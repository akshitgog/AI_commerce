import Link from "next/link";
import { ArrowRight, MessageSquareText, Store } from "lucide-react";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-3xl space-y-10">
        <div className="space-y-3 text-center">
          <p className="text-xs font-medium tracking-widest text-muted-foreground uppercase">
            Test Mode · Prototype
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">
            AI Commerce Gateway
          </h1>
          <p className="mx-auto max-w-xl text-sm leading-6 text-muted-foreground">
            AI proposes. Human buyer authorizes. Merchant independently accepts.
            The trusted backend executes, verifies, and reconciles.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Link href="/buyer" className="group focus-visible:outline-none">
            <Card className="h-full transition-colors group-hover:border-primary/40 group-focus-visible:ring-2 group-focus-visible:ring-ring group-focus-visible:ring-offset-2">
              <CardHeader className="space-y-3">
                <div className="flex size-10 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <MessageSquareText className="size-5" aria-hidden />
                </div>
                <CardTitle className="flex items-center justify-between">
                  Reference Buyer Chat
                  <ArrowRight
                    className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5"
                    aria-hidden
                  />
                </CardTitle>
                <CardDescription>
                  Shop from Demo Electronics with natural language. Approve an
                  exact trusted total, then watch merchant acceptance, payment,
                  verification, and recovery unfold.
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>

          <Link href="/merchant" className="group focus-visible:outline-none">
            <Card className="h-full transition-colors group-hover:border-primary/40 group-focus-visible:ring-2 group-focus-visible:ring-ring group-focus-visible:ring-offset-2">
              <CardHeader className="space-y-3">
                <div className="flex size-10 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <Store className="size-5" aria-hidden />
                </div>
                <CardTitle className="flex items-center justify-between">
                  Merchant Control Center
                  <ArrowRight
                    className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5"
                    aria-hidden
                  />
                </CardTitle>
                <CardDescription>
                  Publish products, set AI-purchase policy, review proposals,
                  and inspect transactions with a structured audit trail.
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>
        </div>

        <p className="text-center text-xs text-muted-foreground">
          All data is a fictional demo fixture. Provider references are mock
          values, not real payment evidence.
        </p>
      </div>
    </main>
  );
}
