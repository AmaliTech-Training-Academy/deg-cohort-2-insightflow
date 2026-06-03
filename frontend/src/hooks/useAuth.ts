import { useState } from "react";
import {
  getToken,
  setToken,
  clearAllTokens,
  getStoredUser,
  setStoredUser,
  clearStoredUser,
} from "@/lib/tokenStorage";
import { logout as logoutApi } from "@/api/auth";
import type { User } from "@/types";

export function useAuth() {
  const [user, setUserState] = useState<User | null>(
    () => getStoredUser<User>()
  );

  const isAuthenticated = Boolean(getToken());

  function saveToken(token: string) {
    setToken(token);
  }

  function setUser(u: User | null) {
    setUserState(u);
    if (u) setStoredUser(u);
    else clearStoredUser();
  }

  async function logout() {
    await logoutApi();
    clearAllTokens();
    clearStoredUser();
    setUserState(null);
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }

  return { user, setUser, isAuthenticated, saveToken, logout };
}
