"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, Loader2, ArrowRight } from "lucide-react";
import { useCommerce } from "@/lib/services/provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { MoneyText } from "@/components/shared/money";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { AlertTriangle } from "lucide-react";
import Link from "next/link";

interface DraftResult {
  title: string;
  description: string;
  price: {
    amount_minor: number;
    currency: string;
  };
  available_quantity: number;
  category: string | null;
  sku: string | null;
}

export default function AICatalogPage() {
  const router = useRouter();
  const { actions } = useCommerce();
  const [inputText, setInputText] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [draft, setDraft] = useState<DraftResult | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [successId, setSuccessId] = useState<string | null>(null);
  const [uploadedImages, setUploadedImages] = useState<File[]>([]);
  const [extractError, setExtractError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!inputText.trim()) return;
    setIsGenerating(true);
    setDraft(null);
    setSuccessId(null);
    try {
      const result = await actions.extractDraft(inputText);
      setDraft(result as DraftResult);
      setExtractError(null); // Clear any previous error
    } catch (error) {
      console.error("Failed to generate draft:", error);
      if (error instanceof ApiError) {
        setExtractError(error.message);
      } else {
        setExtractError("Failed to generate draft. Please try again.");
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCreateDraft = async () => {
    if (!draft) return;
    setIsCreating(true);
    try {
      const product = await actions.createProduct({
        title: draft.title,
        description: draft.description,
        price: { amount_minor: draft.price.amount_minor, currency: draft.price.currency },
        availableQuantity: draft.available_quantity,
        category: draft.category || undefined,
        sku: draft.sku || `SKU-${Date.now()}`,
      });

      // Upload images after product is created
      for (let i = 0; i < uploadedImages.length; i++) {
        await actions.addProductImage(
          product.id,
          {
            file: uploadedImages[i],
            alt: undefined,
            sortOrder: i
          }
        );
      }

      setSuccessId(product.id);
      setUploadedImages([]); // Clear images
    } catch (error) {
      console.error("Failed to create product:", error);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">AI Product Assistant</h2>
        <p className="text-muted-foreground mt-2">
          Create product drafts instantly from natural language descriptions.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="bg-card">
          <CardHeader>
            <CardTitle>Describe Product</CardTitle>
            <CardDescription>
              Paste or type your product details including price, quantity, and specs.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {extractError && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>AI Generation Failed</AlertTitle>
                <AlertDescription>
                  <p className="mb-2">{extractError}</p>
                  <p>
                    You can still{" "}
                    <Link
                      href="/merchant/products/new"
                      className="underline hover:no-underline font-medium"
                    >
                      create products manually
                    </Link>
                    .
                  </p>
                </AlertDescription>
              </Alert>
            )}

            <Textarea
              rows={6}
              placeholder="e.g. Premium USB-C charger, 65W GaN, ₹1,499, 50 units available. Comes with a braided cable."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              className="resize-none"
            />

            <div className="space-y-2">
              <Label>Product Images (Optional)</Label>
              <Input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                multiple
                onChange={(e) => {
                  const files = Array.from(e.target.files || []).slice(0, 3);
                  setUploadedImages(files);
                }}
              />
              <p className="text-sm text-muted-foreground">
                Upload up to 3 images (max 5MB each). JPEG, PNG, WebP, or GIF.
              </p>
              {uploadedImages.length > 0 && (
                <div className="flex gap-2 flex-wrap">
                  {uploadedImages.map((file, idx) => (
                    <div key={idx} className="relative">
                      <img
                        src={URL.createObjectURL(file)}
                        alt={`Preview ${idx + 1}`}
                        className="w-20 h-20 object-cover rounded border"
                      />
                      <button
                        type="button"
                        onClick={() => setUploadedImages(imgs => imgs.filter((_, i) => i !== idx))}
                        className="absolute -top-2 -right-2 bg-destructive text-white rounded-full w-5 h-5 flex items-center justify-center text-xs hover:bg-destructive/90"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <Button
              onClick={handleGenerate}
              disabled={isGenerating || !inputText.trim()}
              className="w-full"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Generate Draft
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        <div className="space-y-6">
          {draft && !successId && (
            <Card className="bg-card border-primary/50 shadow-md">
              <CardHeader>
                <CardTitle>Draft Preview</CardTitle>
                <CardDescription>Review the extracted details before saving.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <h3 className="font-semibold text-lg">{draft.title}</h3>
                  <p className="text-sm text-muted-foreground">{draft.description}</p>
                </div>
                
                <div className="grid grid-cols-2 gap-4 pt-2 border-t">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Price</p>
                    <p className="font-medium">
                      <MoneyText money={draft.price} />
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Quantity</p>
                    <p className="font-medium">{draft.available_quantity}</p>
                  </div>
                  {draft.category && (
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Category</p>
                      <p className="font-medium">{draft.category}</p>
                    </div>
                  )}
                  {draft.sku && (
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">SKU</p>
                      <p className="font-medium">{draft.sku}</p>
                    </div>
                  )}
                </div>

                <Button
                  onClick={handleCreateDraft}
                  disabled={isCreating}
                  className="w-full mt-4"
                >
                  {isCreating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    "Create as Draft Product"
                  )}
                </Button>
              </CardContent>
            </Card>
          )}

          {successId && (
            <Card className="bg-card border-green-500/50 shadow-md">
              <CardHeader>
                <CardTitle className="text-green-600 flex items-center">
                  <Sparkles className="mr-2 h-5 w-5" />
                  Product Saved Successfully
                </CardTitle>
                <CardDescription>
                  Your draft product has been created and is ready for further editing.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  onClick={() => router.push(`/merchant/products/${successId}`)}
                  variant="outline"
                  className="w-full group"
                >
                  Edit Product Details
                  <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
