"use client";

import { useParams } from "next/navigation";

import { ProductEditor } from "@/components/merchant/product-editor";

export default function ProductDetailPage() {
  const params = useParams<{ id: string }>();
  return <ProductEditor mode="edit" productId={params.id} />;
}
