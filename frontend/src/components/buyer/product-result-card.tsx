"use client";

import { useState } from "react";
import { Loader2, Package } from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import { formatMoney } from "@/lib/format";
import { MoneyText } from "@/components/shared/money";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface ProductResultCardProps {
  productId: string;
  busy: boolean;
  onBuy: () => void;
}

export function ProductResultCard({
  productId,
  busy,
  onBuy,
}: ProductResultCardProps) {
  const { state } = useCommerce();
  const [expanded, setExpanded] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  const product = state.products.find((entry) => entry.id === productId);
  if (!product) return null;

  const image =
    product.images.find((entry) => entry.isPrimary) ?? product.images[0];
  const inStock = product.availableQuantity > 0;

  return (
    <Card className="overflow-hidden">
      {image && !imageFailed ? (
        <img
          src={image.url}
          alt={image.alt}
          onError={() => setImageFailed(true)}
          className="h-40 w-full bg-muted object-cover"
        />
      ) : (
        <div
          className="flex h-40 w-full items-center justify-center bg-muted"
          aria-hidden
        >
          <Package className="size-8 text-muted-foreground" />
        </div>
      )}

      <CardContent className="flex flex-col gap-1.5 p-5">
        <p className="text-base font-medium leading-tight">{product.title}</p>
        <p className="text-sm text-muted-foreground">{state.merchant.name}</p>
        <div className="mt-1">
          <MoneyText money={product.price} size="lg" />
        </div>
        <p
          className={cn(
            "flex items-center gap-1.5 text-sm",
            inStock ? "text-muted-foreground" : "font-medium text-warning",
          )}
        >
          {inStock
            ? `In stock · ${product.availableQuantity} available`
            : "Out of stock"}
        </p>
        <p className="line-clamp-1 text-sm text-muted-foreground">
          {product.description}
        </p>
      </CardContent>

      <CardFooter className="justify-end gap-2 p-5 pt-0">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setExpanded((open) => !open)}
          aria-expanded={expanded}
        >
          View details
        </Button>
        <Button size="sm" onClick={onBuy} disabled={busy || !inStock}>
          {busy ? <Loader2 className="animate-spin" aria-hidden /> : null}
          Buy for {formatMoney(product.price)}
        </Button>
      </CardFooter>

      {expanded ? (
        <div className="border-t border-border px-5 py-4 text-sm">
          <p className="leading-6 text-foreground">{product.description}</p>
          <dl className="mt-3 flex flex-col gap-1 text-sm">
            <div className="flex items-center justify-between">
              <dt className="text-muted-foreground">Category</dt>
              <dd>{product.category ?? "General"}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-muted-foreground">Merchant</dt>
              <dd>{state.merchant.name}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-muted-foreground">Availability</dt>
              <dd className="tnum">
                {inStock
                  ? `${product.availableQuantity} available`
                  : "Out of stock"}
              </dd>
            </div>
          </dl>
          <details className="mt-3 text-xs">
            <summary className="cursor-pointer font-medium text-muted-foreground">
              Technical details
            </summary>
            <dl className="mt-2 flex flex-col gap-1 font-mono text-muted-foreground">
              <div className="flex items-center justify-between">
                <dt>SKU</dt>
                <dd className="tnum">{product.sku}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt>Catalog version</dt>
                <dd className="tnum">v{product.version}</dd>
              </div>
            </dl>
          </details>
        </div>
      ) : null}
    </Card>
  );
}
