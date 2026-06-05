import { getToken } from "@/lib/tokenStorage";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

function parseErrorDetail(body: unknown): string {
  if (!body || typeof body !== "object") return "Something went wrong 1.";
  const b = body as Record<string, unknown>;
  // DRF field errors: { email: ["msg"], non_field_errors: ["msg"] }
  const messages: string[] = [];
  for (const value of Object.values(b)) {
    if (Array.isArray(value)) messages.push(...value.map(String));
    else if (typeof value === "string") messages.push(value);
  }
  return messages.join(" ") || "Something went wrong.";
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { skipAuth?: boolean } = {}
): Promise<T> {
  const { skipAuth, ...fetchOptions } = options;
  const token = skipAuth ? null : getToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchOptions.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...fetchOptions, headers });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Unauthorized");
  }

  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = null;
    }
    throw new ApiError(res.status, parseErrorDetail(body));
  }

  return res.json() as Promise<T>;
}
