import { NextResponse } from "next/server";

const KROKI_URL = process.env.KROKI_URL || "http://localhost:8000/kroki";

// POST /api/kroki — proxy to Kroki diagram renderer
export async function POST(request: Request) {
  const body = await request.json();
  const { diagram_type, source, output_format } = body as {
    diagram_type: string;
    source: string;
    output_format: string;
  };

  if (!source) {
    return NextResponse.json({ error: "source is required" }, { status: 400 });
  }

  try {
    const res = await fetch(KROKI_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ diagram_type: diagram_type || "mermaid", source, output_format: output_format || "svg" }),
      signal: AbortSignal.timeout(5000),
    });

    if (!res.ok) {
      return NextResponse.json({ error: `Kroki returned ${res.status}` }, { status: 502 });
    }

    const svg = await res.text();
    return new Response(svg, {
      headers: { "Content-Type": "image/svg+xml" },
    });
  } catch {
    return NextResponse.json({ error: "Kroki server unavailable" }, { status: 503 });
  }
}
