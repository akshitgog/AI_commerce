"use client";

import { useState } from "react";
import { BuyerChatShell } from "@/components/buyer/buyer-chat-shell";
import { useCommerce } from "@/lib/services/provider";
import { Badge } from "@/components/ui/badge";

export default function BuyerPage() {
  const [tab, setTab] = useState<"chat" | "billing">("chat");
  const { state } = useCommerce();

  return (
    <div className="flex h-screen flex-col">
      <div className="flex items-center justify-between border-b p-4 bg-background">
        <h1 className="font-semibold text-lg">Shopper Experience</h1>
        <div className="flex gap-4">
          <button
            className={`px-4 py-2 text-sm font-medium rounded-md ${tab === "chat" ? "bg-primary text-primary-foreground" : "bg-muted"}`}
            onClick={() => setTab("chat")}
          >
            Assistant
          </button>
          <button
            className={`px-4 py-2 text-sm font-medium rounded-md ${tab === "billing" ? "bg-primary text-primary-foreground" : "bg-muted"}`}
            onClick={() => setTab("billing")}
          >
            Billing & Orders
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-hidden">
        {tab === "chat" ? (
          <BuyerChatShell />
        ) : (
          <div className="p-8 overflow-y-auto h-full">
            <h2 className="text-2xl font-bold mb-6">Your Orders</h2>
            {Object.values(state.transactions || {}).length === 0 ? (
              <p className="text-muted-foreground">No orders found.</p>
            ) : (
              <div className="flex flex-col gap-4">
                {Object.values(state.transactions || {}).map((tx: any) => (
                  <div key={tx.id} className="border p-4 rounded-lg flex justify-between items-center shadow-sm">
                    <div>
                      <p className="font-medium">Order ID: {tx.id}</p>
                      <p className="text-sm text-muted-foreground">Product ID: {tx.product_id}</p>
                    </div>
                    <div className="flex gap-4 items-center">
                      <p className="font-semibold">
                        {(tx.price_minor / 100).toLocaleString("en-IN", { style: "currency", currency: tx.currency })}
                      </p>
                      <Badge variant={tx.status === "SUCCEEDED" ? "default" : "secondary"}>{tx.status}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
