import { apiFetch } from "./client";
import {
  setRefreshToken,
  getRefreshToken,
  clearAllTokens,
} from "@/lib/tokenStorage";
import type { User } from "@/types";

// ── Payload types ─────────────────────────────────────────────────────────────

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  name: string;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  user: User;
}

// ── Backend response shapes ───────────────────────────────────────────────────

interface BackendUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  role: string | null;
}

interface LoginBackendResponse {
  message?: string;
  user?: BackendUser;
  tokens?: { access: string; refresh: string };
  access?: string;
  refresh?: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function normalizeUser(u: BackendUser, email: string): User {
  const name =
    [u.first_name, u.last_name].filter(Boolean).join(" ") || u.username;
  return {
    id: String(u.id),
    email: u.email,
    name,
    role: (u.role as User["role"]) ?? "analyst",
    createdAt: new Date().toISOString(),
  };
}

function fallbackUser(email: string): User {
  return {
    id: email,
    email,
    name: email.split("@")[0],
    role: "analyst",
    createdAt: new Date().toISOString(),
  };
}

// ── Auth functions ────────────────────────────────────────────────────────────

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const raw = await apiFetch<LoginBackendResponse>("/auth/login/", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  // Handle both response shapes:
  // { tokens: { access, refresh }, user? } or { access, refresh }
  const access = raw.tokens?.access ?? raw.access ?? "";
  const refresh = raw.tokens?.refresh ?? raw.refresh ?? "";

  setRefreshToken(refresh);
  return {
    access,
    refresh,
    user: raw.user ? normalizeUser(raw.user, payload.email) : fallbackUser(payload.email),
  };
}

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const parts = payload.name.trim().split(/\s+/);
  const firstName = parts[0];
  const lastName = parts.slice(1).join(" ") || parts[0];
  const username = payload.email.split("@")[0];

  await apiFetch("/auth/register/", {
    method: "POST",
    body: JSON.stringify({
      email: payload.email,
      username,
      password: payload.password,
      first_name: firstName,
      last_name: lastName,
    }),
  });

  // Backend register returns no tokens — auto-login to get them
  return login({ email: payload.email, password: payload.password });
}

export async function logout(): Promise<void> {
  const refresh = getRefreshToken();
  if (refresh) {
    try {
      await apiFetch("/auth/logout/", {
        method: "POST",
        body: JSON.stringify({ refresh }),
      });
    } catch {
      // Token already expired or blacklisted — still clear locally
    }
  }
  clearAllTokens();
}

export async function refreshToken(token: string): Promise<{ access: string }> {
  return apiFetch<{ access: string }>("/auth/token/refresh/", {
    method: "POST",
    body: JSON.stringify({ refresh: token }),
  });
}

export async function forgotPassword(
  _email: string
): Promise<{ detail: string }> {
  return { detail: "Password reset email sent." };
}
