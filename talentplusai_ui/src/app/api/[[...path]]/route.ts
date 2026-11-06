import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

/**
 * Proxies same-origin /api/* → Django. App Router handlers run here instead of relying only
 * on next.config rewrites (clearer errors, trailing-slash alignment with Django APPEND_SLASH).
 */
const djangoOrigin = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function buildDjangoUrl(pathSegments: string[] | undefined, search: string): string {
  const parts = pathSegments?.filter(Boolean) ?? [];
  // Django expects trailing slash on these routes (avoids 301 redirect chains).
  const tail = parts.length ? `${parts.join("/")}/` : "";
  return `${djangoOrigin}/api/${tail}${search}`;
}

async function proxy(request: NextRequest, pathSegments: string[] | undefined) {
  const targetUrl = buildDjangoUrl(pathSegments, request.nextUrl.search);

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("connection");

  const init: RequestInit & { duplex?: "half" } = {
    method: request.method,
    headers,
    cache: "no-store",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
    init.duplex = "half";
  }

  let upstream: Response;
  try {
    upstream = await fetch(targetUrl, init);
  } catch {
    return NextResponse.json(
      {
        detail:
          `Cannot reach Django at ${djangoOrigin}. Start: python manage.py runserver 127.0.0.1:8000 (then refresh).`,
      },
      { status: 502 },
    );
  }

  // Buffer the upstream body. Streaming it through NextResponse drops the
  // last two bytes of small Django JSON responses, which breaks JSON.parse
  // on the sign-in page (CSRF token comes back without the closing "}").
  const body = await upstream.arrayBuffer();
  const res = new NextResponse(body, {
    status: upstream.status,
    statusText: upstream.statusText,
  });

  upstream.headers.forEach((value, key) => {
    const k = key.toLowerCase();
    if (
      k === "set-cookie" ||
      k === "transfer-encoding" ||
      k === "content-length" ||
      k === "content-encoding"
    ) {
      return;
    }
    res.headers.set(key, value);
  });
  for (const cookie of upstream.headers.getSetCookie()) {
    res.headers.append("Set-Cookie", cookie);
  }

  return res;
}

type Ctx = { params: Promise<{ path?: string[] }> };

export async function GET(request: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function PUT(request: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function PATCH(request: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function DELETE(request: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}
