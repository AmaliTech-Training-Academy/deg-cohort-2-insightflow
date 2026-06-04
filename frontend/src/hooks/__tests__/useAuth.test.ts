import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAuth } from "@/hooks/useAuth";
import type { User } from "@/types";

vi.mock("@/api/auth", () => ({
  logout: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/tokenStorage", () => ({
  getToken: vi.fn(),
  setToken: vi.fn(),
  clearAllTokens: vi.fn(),
  getStoredUser: vi.fn(),
  setStoredUser: vi.fn(),
  clearStoredUser: vi.fn(),
}));

const mockUser: User = {
  id: "1",
  email: "test@insightflow.io",
  name: "Test User",
  role: "analyst",
  createdAt: "2025-01-01T00:00:00.000Z",
};

async function getTokenStorage() {
  return await import("@/lib/tokenStorage");
}

describe("useAuth", () => {
  beforeEach(() => vi.clearAllMocks());

  it("initializes user from localStorage", async () => {
    const storage = await getTokenStorage();
    vi.mocked(storage.getStoredUser<User>).mockReturnValue(mockUser);

    const { result } = renderHook(() => useAuth());

    expect(result.current.user).toEqual(mockUser);
  });

  it("returns null user when localStorage is empty", async () => {
    const storage = await getTokenStorage();
    vi.mocked(storage.getStoredUser<User>).mockReturnValue(null);

    const { result } = renderHook(() => useAuth());

    expect(result.current.user).toBeNull();
  });

  it("isAuthenticated is true when a token exists", async () => {
    const storage = await getTokenStorage();
    vi.mocked(storage.getToken).mockReturnValue("some-token");
    vi.mocked(storage.getStoredUser<User>).mockReturnValue(null);

    const { result } = renderHook(() => useAuth());

    expect(result.current.isAuthenticated).toBe(true);
  });

  it("isAuthenticated is false when no token exists", async () => {
    const storage = await getTokenStorage();
    vi.mocked(storage.getToken).mockReturnValue(null);
    vi.mocked(storage.getStoredUser<User>).mockReturnValue(null);

    const { result } = renderHook(() => useAuth());

    expect(result.current.isAuthenticated).toBe(false);
  });

  it("setUser persists user to localStorage", async () => {
    const storage = await getTokenStorage();
    vi.mocked(storage.getStoredUser<User>).mockReturnValue(null);

    const { result } = renderHook(() => useAuth());

    act(() => {
      result.current.setUser(mockUser);
    });

    expect(result.current.user).toEqual(mockUser);
    expect(vi.mocked(storage.setStoredUser)).toHaveBeenCalledWith(mockUser);
  });

  it("setUser with null clears localStorage", async () => {
    const storage = await getTokenStorage();
    vi.mocked(storage.getStoredUser<User>).mockReturnValue(mockUser);

    const { result } = renderHook(() => useAuth());

    act(() => {
      result.current.setUser(null);
    });

    expect(result.current.user).toBeNull();
    expect(vi.mocked(storage.clearStoredUser)).toHaveBeenCalled();
  });

  it("logout calls the API, clears tokens and user", async () => {
    const storage = await getTokenStorage();
    vi.mocked(storage.getStoredUser<User>).mockReturnValue(mockUser);
    const { logout: logoutApi } = await import("@/api/auth");

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.logout();
    });

    expect(logoutApi).toHaveBeenCalled();
    expect(vi.mocked(storage.clearAllTokens)).toHaveBeenCalled();
    expect(vi.mocked(storage.clearStoredUser)).toHaveBeenCalled();
    expect(result.current.user).toBeNull();
  });
});
