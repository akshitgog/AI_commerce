"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowDown,
  ArrowUp,
  Package,
  Plus,
  Sparkles,
  Star,
  Trash,
  X,
} from "lucide-react";

import { useCommerce } from "@/lib/services/provider";
import type { Product } from "@/lib/types";
import { formatMoney } from "@/lib/format";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { ProductStatusBadge } from "@/components/shared/status-badge";
import { ConfirmDialog } from "@/components/merchant/confirm-dialog";
import { EmptyState } from "@/components/merchant/empty-state";

const CATEGORIES = ["Chargers", "Keyboards", "Cables", "Accessories", "Other"];

interface Fields {
  sku: string;
  title: string;
  description: string;
  category: string;
  priceRupees: string;
  stock: string;
}

const EMPTY_FIELDS: Fields = {
  sku: "",
  title: "",
  description: "",
  category: "",
  priceRupees: "",
  stock: "",
};

function fieldsFromProduct(product: Product): Fields {
  return {
    sku: product.sku,
    title: product.title,
    description: product.description,
    category: product.category ?? "",
    // Display-only derivation for the merchant's own catalog input.
    priceRupees: (product.price.amount_minor / 100).toString(),
    stock: product.availableQuantity.toString(),
  };
}

function validate(fields: Fields, mode: "create" | "edit"): string | null {
  if (fields.title.trim() === "") return "Title is required.";
  if (mode === "create" && fields.sku.trim() === "") return "SKU is required.";
  const price = Number(fields.priceRupees);
  if (fields.priceRupees.trim() === "" || !Number.isFinite(price) || price < 0) {
    return "Enter a valid price in INR.";
  }
  const stock = Number(fields.stock);
  if (
    fields.stock.trim() === "" ||
    !Number.isInteger(stock) ||
    stock < 0
  ) {
    return "Enter a valid whole-number stock quantity.";
  }
  return null;
}

export function ProductEditor({
  mode,
  productId,
}: {
  mode: "create" | "edit";
  productId?: string;
}) {
  const router = useRouter();
  const { state, actions } = useCommerce();

  const product =
    mode === "edit"
      ? state.products.find((p) => p.id === productId)
      : undefined;

  const [fields, setFields] = useState<Fields>(() =>
    product ? fieldsFromProduct(product) : EMPTY_FIELDS
  );
  const [baseline, setBaseline] = useState<Fields>(() =>
    product ? fieldsFromProduct(product) : EMPTY_FIELDS
  );
  const [saving, setSaving] = useState(false);
  const [savedNotice, setSavedNotice] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [confirmLeave, setConfirmLeave] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [pubBusy, setPubBusy] = useState(false);
  const [pubError, setPubError] = useState<string | null>(null);

  const [imageUrl, setImageUrl] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageAlt, setImageAlt] = useState("");
  const [imageBusy, setImageBusy] = useState(false);
  const [imageError, setImageError] = useState<string | null>(null);
  const [imageAddedNotice, setImageAddedNotice] = useState(false);

  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [suggestBusy, setSuggestBusy] = useState(false);
  const [suggestError, setSuggestError] = useState<string | null>(null);
  const hydratedProductId = useRef<string | null>(null);

  useEffect(() => {
    if (product && hydratedProductId.current !== product.id) {
      const loaded = fieldsFromProduct(product);
      setFields(loaded);
      setBaseline(loaded);
      hydratedProductId.current = product.id;
    }
  }, [product]);

  if (mode === "edit" && !product) {
    return (
      <EmptyState
        icon={Package}
        title="Product not found"
        description="This product may have been deleted."
        action={
          <Button variant="outline" onClick={() => router.push("/merchant/products")}>
            Back to products
          </Button>
        }
      />
    );
  }

  const dirty = JSON.stringify(fields) !== JSON.stringify(baseline);
  const images = product ? [...product.images].sort((a, b) => a.position - b.position) : [];

  function set<K extends keyof Fields>(key: K, value: string) {
    setFields((f) => ({ ...f, [key]: value }));
    setValidationError(null);
    setSavedNotice(false);
  }

  function handleCancel() {
    if (dirty) {
      setConfirmLeave(true);
    } else {
      router.push("/merchant/products");
    }
  }

  async function handleSave() {
    const error = validate(fields, mode);
    if (error) {
      setValidationError(error);
      return;
    }
    setSaving(true);
    setSaveError(null);
    setConflict(false);
    // Catalog authoring only: convert the merchant's ₹ input to paise minor
    // units for the Money contract. This is not transaction authority.
    const price = {
      amount_minor: Math.round(Number(fields.priceRupees) * 100),
      currency: "INR",
    };
    const availableQuantity = Number(fields.stock);
    try {
      if (mode === "create") {
        const created = await actions.createProduct({
          sku: fields.sku.trim(),
          title: fields.title.trim(),
          description: fields.description.trim(),
          category: fields.category || null,
          price,
          availableQuantity,
        });
        router.push(`/merchant/products/${created.id}`);
      } else if (product) {
        await actions.updateProduct(product.id, {
          title: fields.title.trim(),
          description: fields.description.trim(),
          category: fields.category || null,
          price,
          availableQuantity,
          version: product.version,
        });
        setBaseline(fields);
        setSavedNotice(true);
        window.setTimeout(() => setSavedNotice(false), 4000);
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : "Save failed.";
      if (message.includes("VERSION_CONFLICT")) {
        setConflict(true);
      } else {
        setSaveError(message);
      }
    } finally {
      setSaving(false);
    }
  }

  function handleReload() {
    if (!product) return;
    const fresh = fieldsFromProduct(product);
    setFields(fresh);
    setBaseline(fresh);
    setConflict(false);
  }

  async function handlePublishToggle() {
    if (!product) return;
    setPubBusy(true);
    setPubError(null);
    try {
      if (product.status === "PUBLISHED") {
        await actions.unpublishProduct(product.id);
      } else {
        await actions.publishProduct(product.id);
      }
    } catch (e) {
      setPubError(e instanceof Error ? e.message : "Publication failed.");
    } finally {
      setPubBusy(false);
    }
  }

  async function handleDelete() {
    if (!product) return;
    setDeleting(true);
    try {
      await actions.deleteDraft(product.id);
      router.push("/merchant/products");
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Delete failed.");
      setConfirmDelete(false);
    } finally {
      setDeleting(false);
    }
  }

  async function handleAddImage() {
    if (!product || images.length >= 3) return;
    if (!imageFile && imageUrl.trim() === "") return;

    setImageBusy(true);
    setImageError(null);
    try {
      if (imageFile) {
        // Upload file directly
        await actions.addProductImage(product.id, {
          file: imageFile,
          alt: imageAlt.trim() || product.title,
        });
      } else {
        // Use URL
        await actions.addProductImage(product.id, {
          url: imageUrl.trim(),
          alt: imageAlt.trim() || product.title,
        });
      }
      setImageFile(null);
      setImageUrl("");
      setImageAlt("");
      // Bug 4 fix: show a success notice so the merchant sees confirmation
      // that the image was added (images persist immediately via their own API
      // call, so the text-field Save button's disabled state is irrelevant).
      setImageAddedNotice(true);
      window.setTimeout(() => setImageAddedNotice(false), 4000);
    } catch (e) {
      setImageError(e instanceof Error ? e.message : "Could not add image.");
    } finally {
      setImageBusy(false);
    }
  }

  async function handleMoveImage(index: number, direction: -1 | 1) {
    if (!product) return;
    const ids = images.map((i) => i.id);
    const target = index + direction;
    if (target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    setImageError(null);
    try {
      await actions.reorderProductImages(product.id, ids);
    } catch (e) {
      setImageError(e instanceof Error ? e.message : "Could not reorder images.");
    }
  }

  async function handleRemoveImage(imageId: string) {
    if (!product) return;
    setImageError(null);
    try {
      await actions.removeProductImage(product.id, imageId);
    } catch (e) {
      setImageError(e instanceof Error ? e.message : "Could not remove image.");
    }
  }

  async function handleSuggest() {
    if (!product) return;
    setSuggestBusy(true);
    setSuggestError(null);
    try {
      const text = await actions.suggestDescription(product.id);
      setSuggestion(text);
    } catch (e) {
      setSuggestError(
        e instanceof Error ? e.message : "Could not generate a suggestion."
      );
    } finally {
      setSuggestBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="outline" size="sm" onClick={handleCancel}>
          Cancel
        </Button>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-lg font-semibold">
            {mode === "create" ? "New product" : product?.title}
          </h2>
          {product ? (
            <p className="tnum font-mono text-xs text-muted-foreground">
              {product.sku} · v{product.version}
            </p>
          ) : (
            <p className="text-xs text-muted-foreground">
              Created as a draft — publish when ready.
            </p>
          )}
        </div>
        {product ? (
          <Button
            variant="outline"
            className="text-destructive hover:text-destructive"
            onClick={() => setConfirmDelete(true)}
          >
            <Trash aria-hidden />
            {product.status === "PUBLISHED" ? "Delete product" : "Delete draft"}
          </Button>
        ) : null}
        <Button onClick={() => void handleSave()} disabled={saving || (mode === "edit" && !dirty)}>
          {saving ? "Saving…" : mode === "create" ? "Create product" : "Save changes"}
        </Button>
      </div>

      {/* Notices */}
      <div aria-live="polite" className="space-y-3">
        {validationError ? (
          <Alert variant="warning" role="alert">
            <AlertTitle>Check the form</AlertTitle>
            <AlertDescription>{validationError}</AlertDescription>
          </Alert>
        ) : null}
        {saveError ? (
          <Alert variant="destructive" role="alert">
            <AlertTitle>Save failed</AlertTitle>
            <AlertDescription>{saveError}</AlertDescription>
          </Alert>
        ) : null}
        {conflict ? (
          <Alert variant="warning" role="alert">
            <AlertTitle>Version conflict</AlertTitle>
            <AlertDescription className="flex flex-wrap items-center gap-2">
              This product was changed elsewhere. Reload to get the latest
              version.
              <Button size="sm" variant="outline" onClick={handleReload}>
                Reload
              </Button>
            </AlertDescription>
          </Alert>
        ) : null}
        {savedNotice ? (
          <Alert variant="success">
            <AlertTitle>Saved</AlertTitle>
            <AlertDescription>
              Your changes were saved as a new product version.
            </AlertDescription>
          </Alert>
        ) : null}
        {pubError ? (
          <Alert variant="warning" role="alert">
            <AlertTitle>Not ready to publish</AlertTitle>
            <AlertDescription>{pubError}</AlertDescription>
          </Alert>
        ) : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main column */}
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Product information</CardTitle>
              <CardDescription>
                Details an AI buyer reads when discovering your catalog.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="pe-title">Title</Label>
                <Input
                  id="pe-title"
                  value={fields.title}
                  onChange={(e) => set("title", e.target.value)}
                  placeholder="65W USB-C Charger"
                />
              </div>

              {mode === "create" ? (
                <div className="space-y-2">
                  <Label htmlFor="pe-sku">SKU</Label>
                  <Input
                    id="pe-sku"
                    value={fields.sku}
                    onChange={(e) => set("sku", e.target.value)}
                    placeholder="USB-C-65W-001"
                    className="font-mono"
                  />
                </div>
              ) : null}

              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <Label htmlFor="pe-description">Description</Label>
                  {product ? (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => void handleSuggest()}
                      disabled={suggestBusy}
                    >
                      <Sparkles aria-hidden />
                      {suggestBusy ? "Suggesting…" : "Suggest description"}
                    </Button>
                  ) : null}
                </div>
                <Textarea
                  id="pe-description"
                  value={fields.description}
                  onChange={(e) => set("description", e.target.value)}
                  rows={4}
                  placeholder="What the product is, key specs, compatibility."
                />
                <p className="text-xs text-muted-foreground">
                  AI suggestions never change price, stock, or publication.
                </p>
                {suggestError ? (
                  <p className="text-sm text-destructive" role="alert">
                    {suggestError}
                  </p>
                ) : null}
                {suggestion ? (
                  <div className="space-y-2 rounded-md border bg-muted/50 p-3">
                    <p className="text-xs font-medium text-muted-foreground">
                      Suggested description — review before applying
                    </p>
                    <p className="text-sm">{suggestion}</p>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          set("description", suggestion);
                          setSuggestion(null);
                        }}
                      >
                        Use suggestion
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => setSuggestion(null)}
                      >
                        Dismiss
                      </Button>
                    </div>
                  </div>
                ) : null}
              </div>

              <div className="space-y-2">
                <Label htmlFor="pe-category">Category</Label>
                <Select
                  value={fields.category}
                  onValueChange={(v) => set("category", v)}
                >
                  <SelectTrigger id="pe-category" className="w-full">
                    <SelectValue placeholder="Select a category" />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Images</CardTitle>
              <CardDescription>
                1–3 images. The first image is the primary image buyers see.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {mode === "create" ? (
                <p className="text-sm text-muted-foreground">
                  Save the product first to add images.
                </p>
              ) : (
                <>
                  {images.length === 0 ? (
                    <p className="rounded-md border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
                      No images yet. Add at least one image before publishing.
                    </p>
                  ) : (
                    <ul className="space-y-3">
                      {images.map((image, index) => (
                        <li
                          key={image.id}
                          className="flex items-center gap-3 rounded-md border p-2"
                        >
                          {/* eslint-disable-next-line @next/next/no-img-element -- prototype: merchant-provided URLs */}
                          <img
                            src={image.url}
                            alt={image.alt}
                            className="size-14 shrink-0 rounded-md border object-cover"
                          />
                          <div className="min-w-0 flex-1">
                            <p className="flex items-center gap-1.5 text-sm font-medium">
                              {index === 0 ? (
                                <span className="inline-flex items-center gap-1 text-xs font-medium text-primary">
                                  <Star className="size-3" aria-hidden />
                                  Primary
                                </span>
                              ) : (
                                <span className="text-xs text-muted-foreground">
                                  Image {index + 1}
                                </span>
                              )}
                            </p>
                            <p className="truncate text-xs text-muted-foreground">
                              {image.alt}
                            </p>
                          </div>
                          <div className="flex items-center gap-1">
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              aria-label={`Move image ${index + 1} up`}
                              disabled={index === 0}
                              onClick={() => void handleMoveImage(index, -1)}
                            >
                              <ArrowUp aria-hidden />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              aria-label={`Move image ${index + 1} down`}
                              disabled={index === images.length - 1}
                              onClick={() => void handleMoveImage(index, 1)}
                            >
                              <ArrowDown aria-hidden />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              aria-label={`Remove image ${index + 1}`}
                              onClick={() => void handleRemoveImage(image.id)}
                            >
                              <X aria-hidden />
                            </Button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}

                  {images.length < 3 ? (
                    <>
                      <Separator />
                      <div className="space-y-3">
                        <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
                          <div className="space-y-1">
                            <Label htmlFor="pe-image-file">Upload Image File</Label>
                            <Input
                              id="pe-image-file"
                              type="file"
                              accept="image/jpeg,image/png,image/webp,image/gif"
                              onChange={(e) => {
                                const file = e.target.files?.[0];
                                if (file) {
                                  if (file.size > 5 * 1024 * 1024) {
                                    setImageError("Image must be 5MB or smaller.");
                                    e.target.value = "";
                                    return;
                                  }
                                  setImageFile(file);
                                  setImageUrl(""); // Clear URL if file selected
                                  setImageError(null);
                                }
                              }}
                              disabled={imageBusy}
                            />
                            <p className="text-xs text-muted-foreground">
                              PNG, JPEG, WebP, or GIF. Max 5MB.
                            </p>
                          </div>
                          <div className="flex items-end">
                            <Button
                              type="button"
                              variant="secondary"
                              onClick={() => void handleAddImage()}
                              disabled={imageBusy || (!imageFile && imageUrl.trim() === "")}
                            >
                              <Plus aria-hidden />
                              {imageBusy ? "Adding…" : "Add"}
                            </Button>
                          </div>
                        </div>

                        <div className="relative">
                          <div className="absolute inset-0 flex items-center">
                            <span className="w-full border-t" />
                          </div>
                          <div className="relative flex justify-center text-xs uppercase">
                            <span className="bg-background px-2 text-muted-foreground">Or use URL</span>
                          </div>
                        </div>

                        <div className="grid gap-2 sm:grid-cols-[2fr_1fr]">
                          <div className="space-y-1">
                            <Label htmlFor="pe-image-url">Image URL</Label>
                            <Input
                              id="pe-image-url"
                              value={imageUrl}
                              onChange={(e) => {
                                setImageUrl(e.target.value);
                                if (e.target.value.trim()) {
                                  setImageFile(null); // Clear file if URL entered
                                }
                              }}
                              placeholder="https://…"
                              inputMode="url"
                              disabled={imageBusy}
                            />
                          </div>
                          <div className="space-y-1">
                            <Label htmlFor="pe-image-alt">Alt text (optional)</Label>
                            <Input
                              id="pe-image-alt"
                              value={imageAlt}
                              onChange={(e) => setImageAlt(e.target.value)}
                              placeholder="Describe the image"
                              disabled={imageBusy}
                            />
                          </div>
                        </div>
                      </div>
                    </>
                  ) : null}
                  {imageError ? (
                    <p className="text-sm text-destructive" role="alert">
                      {imageError}
                    </p>
                  ) : null}
                  {imageAddedNotice ? (
                    <Alert variant="success">
                      <AlertTitle>Image added</AlertTitle>
                      <AlertDescription>
                        The image was uploaded and saved immediately.
                      </AlertDescription>
                    </Alert>
                  ) : null}
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Side column */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Pricing</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Label htmlFor="pe-price">Price (INR)</Label>
              <Input
                id="pe-price"
                type="number"
                min="0"
                step="0.01"
                inputMode="decimal"
                className="tnum"
                value={fields.priceRupees}
                onChange={(e) => set("priceRupees", e.target.value)}
                placeholder="899"
              />
              <p className="text-xs text-muted-foreground">
                Entered in rupees, stored as paise.{" "}
                {fields.priceRupees !== "" &&
                Number.isFinite(Number(fields.priceRupees))
                  ? formatMoney({
                      amount_minor: Math.round(Number(fields.priceRupees) * 100),
                      currency: "INR",
                    })
                  : null}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Inventory</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Label htmlFor="pe-stock">Stock</Label>
              <Input
                id="pe-stock"
                type="number"
                min="0"
                step="1"
                inputMode="numeric"
                className="tnum"
                value={fields.stock}
                onChange={(e) => set("stock", e.target.value)}
                placeholder="10"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Publication</CardTitle>
              <CardDescription>
                Only published products are discoverable by AI buyers.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {product ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Status</span>
                    <ProductStatusBadge status={product.status} />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Version</span>
                    <span className="tnum font-mono text-sm">v{product.version}</span>
                  </div>
                  <Button
                    className="w-full"
                    variant={product.status === "PUBLISHED" ? "outline" : "default"}
                    disabled={pubBusy}
                    onClick={() => void handlePublishToggle()}
                  >
                    {pubBusy
                      ? "Working…"
                      : product.status === "PUBLISHED"
                        ? "Unpublish"
                        : "Publish"}
                  </Button>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  The product is created as a draft. Publish it from here after
                  saving.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={confirmLeave}
        onOpenChange={setConfirmLeave}
        title="Discard unsaved changes?"
        description="You have unsaved changes. Leaving now will discard them."
        confirmLabel="Discard changes"
        destructive
        onConfirm={() => router.push("/merchant/products")}
      />

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title={product?.status === "PUBLISHED" ? "Delete product?" : "Delete draft?"}
        description={`"${fields.title}" will be permanently removed. This cannot be undone.`}
        confirmLabel={product?.status === "PUBLISHED" ? "Delete product" : "Delete draft"}
        destructive
        busy={deleting}
        onConfirm={() => void handleDelete()}
      />
    </div>
  );
}
