import { useState } from "react";
import { getToken, setToken, clearToken } from "@/lib/tokenStorage";
import type { User } from "@/types";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);

  const isAuthenticated = Boolean(getToken());

  function saveToken(token: string) {
    setToken(token);
  }

  function logout() {
    clearToken();
    setUser(null);
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  return { user, setUser, isAuthenticated, saveToken, logout };
}
