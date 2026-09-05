"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Ellipsis, Eye, Package, Pencil, Plus, Trash } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import type { Product } from "@/lib/types";
import { formatRelativeTime } from "@/lib/format";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { MoneyText } from "@/components/shared/money";
import { ProductStatusBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/merchant/empty-state";
import { ConfirmDialog } from "@/components/merchant/confirm-dialog";

function ProductThumb({ product }: { product: Product }) {
  const primary = product.images.find((i) => i.isPrimary) ?? product.images[0];
  if (!primary) {
    return (
      <div className="flex size-14 shrink-0 items-center justify-center rounded-md border bg-muted">
        <Package className="size-5 text-muted-foreground" aria-hidden />
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element -- prototype: merchant-provided URLs
    <img
      src={primary.url}
      alt={primary.alt}
      className="size-14 shrink-0 rounded-md border object-cover"
    />
  );
}

export default function ProductsPage() {
  const router = useRouter();
  const { state, actions } = useCommerce();

  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Product | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [exporting, setExporting] = useState(false);
  
  // New state for multi-select
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const products = [...state.products].sort((a, b) =>
    b.id.localeCompare(a.id)
  );

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(products.map(p => p.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleSelectOne = (id: string, checked: boolean) => {
    const newSelected = new Set(selectedIds);
    if (checked) {
      newSelected.add(id);
    } else {
      newSelected.delete(id);
    }
    setSelectedIds(newSelected);
  };

  async function handlePublish(product: Product) {
    setActionError(null);
    setBusyId(product.id);
    try {
      if (product.status === "PUBLISHED") {
        await actions.unpublishProduct(product.id);
      } else {
        await actions.publishProduct(product.id);
      }
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Action failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    setActionError(null);
    try {
      if (deleteTarget.status === "PUBLISHED") {
        await actions.unpublishProduct(deleteTarget.id);
      }
      await actions.deleteDraft(deleteTarget.id);
      setDeleteTarget(null);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Delete failed.");
    } finally {
      setDeleting(false);
    }
  }

  const handleExportZip = async () => {
    setExporting(true);
    setActionError(null);
    try {
      const JSZip = (await import("jszip")).default;
      const { saveAs } = await import("file-saver");
      const zip = new JSZip();
      
      const targetProducts = selectedIds.size > 0 
        ? state.products.filter(p => selectedIds.has(p.id))
        : state.products;

      const csvRows = ["ID,SKU,Title,Price,Status,Quantity"];
      targetProducts.forEach(p => {
        csvRows.push(`${p.id},${p.sku},"${p.title.replace(/"/g, "")}",${p.price.amount_minor},${p.status},${p.availableQuantity}`);
      });
      zip.file("catalog.csv", csvRows.join("\n"));
      
      const imgFolder = zip.folder("images");
      for (const p of targetProducts) {
        for (const img of p.images) {
          try {
             const res = await fetch(img.url);
             if (res.ok) {
                const blob = await res.blob();
                imgFolder?.file(`${p.id}_${img.id}.jpg`, blob);
             }
          } catch (e) {
             // Silently skip on error
          }
        }
      }
      
      const content = await zip.generateAsync({type:"blob"});
      saveAs(content, "catalog_export.zip");
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <>
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Products</h2>
          <p className="text-sm text-muted-foreground">
            <span className="tnum">{products.length}</span> products in your
            AI-readable catalog.
          </p>
        </div>
        <div className="flex gap-2">
            <Button variant="outline" onClick={handleExportZip} disabled={exporting} aria-label="Export catalog ZIP">
                {exporting ? "Exporting…" : (selectedIds.size > 0 ? `Export ZIP (${selectedIds.size})` : "Export All to ZIP")}
            </Button>
            <Button asChild>
              <Link href="/merchant/products/new">
                <Plus aria-hidden />
                Add product
              </Link>
            </Button>
          </div>
      </div>

      {actionError ? (
        <Alert variant="warning" role="alert">
          <AlertTitle>Action could not be completed</AlertTitle>
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      ) : null}

      {products.length === 0 ? (
        <EmptyState
          icon={Package}
          title="No products yet"
          description="Publish a product with a price, stock, and at least one image so AI buyers can discover it."
          action={
            <Button asChild>
              <Link href="/merchant/products/new">
                <Plus aria-hidden />
                Add product
              </Link>
            </Button>
          }
        />
      ) : (
        <div className="max-h-[70vh] overflow-auto rounded-md border bg-card">
          <Table>
            <TableHeader className="sticky top-0 z-10 bg-card shadow-[inset_0_-1px_0_var(--color-border)]">
              <TableRow>
                <TableHead className="w-[40px] px-4">
                  <input 
                    type="checkbox" 
                    className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                    checked={selectedIds.size === products.length && products.length > 0}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    aria-label="Select all products"
                  />
                </TableHead>
                <TableHead>Product</TableHead>
                <TableHead>SKU</TableHead>
                <TableHead>Price</TableHead>
                <TableHead>Stock</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Version</TableHead>
                
                <TableHead className="w-10">
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {products.map((product) => (
                <TableRow key={product.id} className={selectedIds.has(product.id) ? "bg-muted/30" : ""}>
                  <TableCell className="px-4">
                    <input 
                      type="checkbox" 
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                      checked={selectedIds.has(product.id)}
                      onChange={(e) => handleSelectOne(product.id, e.target.checked)}
                      aria-label={`Select ${product.title}`}
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <ProductThumb product={product} />
                      <div className="min-w-0">
                        <Link
                          href={`/merchant/products/${product.id}`}
                          className="block truncate text-sm font-medium text-foreground underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          {product.title}
                        </Link>
                        <p className="text-xs text-muted-foreground">
                          {product.category ?? "Uncategorized"}
                        </p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="tnum font-mono text-xs">
                    {product.sku}
                  </TableCell>
                  <TableCell>
                    <MoneyText money={product.price} />
                  </TableCell>
                  <TableCell>
                    {product.availableQuantity === 0 ? (
                      <Badge variant="warning">Out of stock</Badge>
                    ) : (
                      <span className="tnum">{product.availableQuantity}</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <ProductStatusBadge status={product.status} />
                  </TableCell>
                  <TableCell className="tnum font-mono text-xs text-muted-foreground">
                    v{product.version}
                  </TableCell>
                  
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Actions for ${product.title}`}
                          disabled={busyId === product.id}
                        >
                          <Ellipsis aria-hidden />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onSelect={() =>
                            router.push(`/merchant/products/${product.id}`)
                          }
                        >
                          <Eye aria-hidden />
                          View
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={() =>
                            router.push(`/merchant/products/${product.id}`)
                          }
                        >
                          <Pencil aria-hidden />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={() => void handlePublish(product)}
                        >
                          {product.status === "PUBLISHED"
                            ? "Unpublish"
                            : "Publish"}
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onSelect={() => setDeleteTarget(product)}
                        >
                          <Trash aria-hidden />
                          {product.status === "PUBLISHED" ? "Delete product" : "Delete draft"}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title={deleteTarget?.status === "PUBLISHED" ? "Delete product?" : "Delete draft?"}
        description={
          deleteTarget
            ? `"${deleteTarget.title}" will be permanently removed. This cannot be undone.`
            : undefined
        }
        confirmLabel={deleteTarget?.status === "PUBLISHED" ? "Delete product" : "Delete draft"}
        destructive
        busy={deleting}
        onConfirm={() => void handleDelete()}
      />
    </>
  );
}
