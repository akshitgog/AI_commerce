const backendOrigin = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

export async function POST() {
  

  const issuerKey = process.env.BUYER_SESSIONS_ISSUER_KEY || "dev_key_123";
  const buyerId = process.env.E2E_BUYER_ID || "buyer_1";
  if (!issuerKey || !buyerId) {
    return Response.json(
      { error: "E2E buyer session is not configured" },
      { status: 503 },
    );
  }

  try {
    const response = await fetch(`${backendOrigin}/v1/buyer/sessions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Issuer-Key": issuerKey,
      },
      body: JSON.stringify({ buyer_id: buyerId }),
      cache: "no-store",
    });
    const payload = await response.arrayBuffer();

    return new Response(payload, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") ?? "application/json",
      },
    });
  } catch {
    return Response.json(
      { error: "Buyer session service unavailable" },
      { status: 502 },
    );
  }
}
