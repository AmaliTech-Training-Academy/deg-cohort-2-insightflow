// Real calls: import { apiFetch } from "./client";
// Base path: /api/auth/
import type { User } from "@/types";

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

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  // POST /api/auth/login/
  return {
    access: "mock-access-token",
    refresh: "mock-refresh-token",
    user: {
      id: "1",
      email: payload.email,
      name: "Demo User",
      role: "admin",
      createdAt: new Date().toISOString(),
    },
  };
}

export async function register(
  payload: RegisterPayload
): Promise<AuthResponse> {
  // POST /api/auth/register/
  return {
    access: "mock-access-token",
    refresh: "mock-refresh-token",
    user: {
      id: "2",
      email: payload.email,
      name: payload.name,
      role: "analyst",
      createdAt: new Date().toISOString(),
    },
  };
}

export async function me(): Promise<User> {
  // GET /api/auth/me/
  return {
    id: "1",
    email: "demo@insightflow.io",
    name: "Demo User",
    role: "admin",
    createdAt: new Date().toISOString(),
  };
}

export async function refreshToken(
  _token: string
): Promise<{ access: string }> {
  // POST /api/auth/refresh/
  return { access: "mock-new-access-token" };
}
