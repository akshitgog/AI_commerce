"use client";

import { useState } from "react";
import { BuyerChatShell } from "@/components/buyer/buyer-chat-shell";
import { useCommerce } from "@/lib/services/provider";
import { TransactionStatusBadge } from "@/components/shared/status-badge";
import { MoneyText } from "@/components/shared/money";
import type { Transaction } from "@/lib/types";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatMoney } from "@/lib/format";

export default function BuyerPage() {
  const [tab, setTab] = useState<"chat" | "billing">("chat");
  const { state } = useCommerce();
  const [selectedTxIds, setSelectedTxIds] = useState<Set<string>>(new Set());

  const exportBillingCSV = (transactions: Transaction[]) => {
    const headers = ["Order ID", "Product ID", "Amount (minor)", "Currency", "Status", "Created At"];
    const rows = transactions.map(tx => [
      tx.id,
      tx.productId,
      tx.amount.amount_minor,
      tx.amount.currency,
      tx.state,
      tx.createdAt || ""
    ]);
    const csvContent = [headers, ...rows].map(e => e.join(",")).join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "billing.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportBillingJSON = (transactions: Transaction[]) => {
    const jsonContent = JSON.stringify(transactions, null, 2);
    const blob = new Blob([jsonContent], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "billing.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      const allTxIds = Object.keys(state.transactions);
      setSelectedTxIds(new Set(allTxIds));
    } else {
      setSelectedTxIds(new Set());
    }
  };

  const handleSelectOne = (id: string, checked: boolean) => {
    const newSelected = new Set(selectedTxIds);
    if (checked) {
      newSelected.add(id);
    } else {
      newSelected.delete(id);
    }
    setSelectedTxIds(newSelected);
  };

  const txList = Object.values(state.transactions);
  const selectedTransactions = txList.filter(tx => selectedTxIds.has(tx.id));

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
        <div className={tab === "chat" ? "h-full" : "hidden"}>
          <BuyerChatShell />
        </div>
        <div className={tab === "billing" ? "p-8 overflow-y-auto h-full" : "hidden"}>
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold">Your Orders</h2>
            {selectedTxIds.size > 0 && (
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium">{selectedTxIds.size} selected</span>
                <Button variant="outline" size="sm" onClick={() => exportBillingCSV(selectedTransactions)}>
                  <Download className="h-4 w-4 mr-2" />
                  Download CSV
                </Button>
                <Button variant="outline" size="sm" onClick={() => exportBillingJSON(selectedTransactions)}>
                  <Download className="h-4 w-4 mr-2" />
                  Download JSON
                </Button>
              </div>
            )}
          </div>
          {txList.length === 0 ? (
            <p className="text-muted-foreground">No orders found.</p>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-4 px-4">
                <input 
                  type="checkbox" 
                  checked={selectedTxIds.size === txList.length && txList.length > 0} 
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <span className="text-sm font-medium">Select All</span>
              </div>
              {txList.map((tx: Transaction) => (
                <div key={tx.id} className="border p-4 rounded-lg flex items-center shadow-sm gap-4">
                  <input 
                    type="checkbox" 
                    checked={selectedTxIds.has(tx.id)} 
                    onChange={(e) => handleSelectOne(tx.id, e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                  />
                  <div className="flex flex-1 justify-between items-center">
                    <div>
                      <p className="font-medium">Order ID: {tx.id}</p>
                      <p className="text-sm text-muted-foreground">Product ID: {tx.productId}</p>
                    </div>
                    <div className="flex gap-4 items-center">
                      <p className="font-semibold">
                        <MoneyText money={tx.amount} />
                      </p>
                      <TransactionStatusBadge state={tx.state} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
