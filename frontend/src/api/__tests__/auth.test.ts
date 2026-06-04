import { describe, it, expect, vi, beforeEach } from "vitest";
import { login, register, logout, refreshToken } from "@/api/auth";

vi.mock("@/api/client", () => ({
  apiFetch: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number;
    detail: string;
    constructor(status: number, detail: string) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  },
}));

vi.mock("@/lib/tokenStorage", () => ({
  setRefreshToken: vi.fn(),
  getRefreshToken: vi.fn(),
  clearAllTokens: vi.fn(),
}));

const mockBackendUser = {
  id: 7,
  username: "testuser",
  email: "test@insightflow.io",
  first_name: "Test",
  last_name: "User",
  is_active: true,
  role: "analyst",
};

async function getApiFetch() {
  const { apiFetch } = await import("@/api/client");
  return vi.mocked(apiFetch);
}

describe("login", () => {
  beforeEach(() => vi.clearAllMocks());

  it("POSTs to /auth/login/ with email and password", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({
      message: "Login successful",
      user: mockBackendUser,
      tokens: { access: "acc", refresh: "ref" },
    });

    await login({ email: "test@insightflow.io", password: "Secret@1" });

    expect(apiFetch).toHaveBeenCalledWith("/auth/login/", {
      method: "POST",
      body: JSON.stringify({ email: "test@insightflow.io", password: "Secret@1" }),
    });
  });

  it("normalizes backend user shape to frontend User type", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({
      message: "Login successful",
      user: mockBackendUser,
      tokens: { access: "acc", refresh: "ref" },
    });

    const result = await login({ email: "test@insightflow.io", password: "Secret@1" });

    expect(result.user.id).toBe("7");
    expect(result.user.name).toBe("Test User");
    expect(result.user.email).toBe("test@insightflow.io");
    expect(result.user.role).toBe("analyst");
  });

  it("extracts access and refresh from tokens wrapper", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({
      message: "Login successful",
      user: mockBackendUser,
      tokens: { access: "access-token", refresh: "refresh-token" },
    });

    const result = await login({ email: "test@insightflow.io", password: "Secret@1" });

    expect(result.access).toBe("access-token");
    expect(result.refresh).toBe("refresh-token");
  });

  it("stores the refresh token", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({
      message: "Login successful",
      user: mockBackendUser,
      tokens: { access: "acc", refresh: "ref" },
    });
    const { setRefreshToken } = await import("@/lib/tokenStorage");

    await login({ email: "test@insightflow.io", password: "Secret@1" });

    expect(vi.mocked(setRefreshToken)).toHaveBeenCalledWith("ref");
  });

  it("falls back to username when first_name and last_name are empty", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({
      message: "Login successful",
      user: { ...mockBackendUser, first_name: "", last_name: "" },
      tokens: { access: "acc", refresh: "ref" },
    });

    const result = await login({ email: "test@insightflow.io", password: "Secret@1" });

    expect(result.user.name).toBe("testuser");
  });
});

describe("register", () => {
  beforeEach(() => vi.clearAllMocks());

  it("POSTs to /auth/register/ with split name and email-derived username", async () => {
    const apiFetch = await getApiFetch();
    apiFetch
      .mockResolvedValueOnce({ message: "User registered successfully", user: mockBackendUser })
      .mockResolvedValueOnce({
        message: "Login successful",
        user: mockBackendUser,
        tokens: { access: "acc", refresh: "ref" },
      });

    await register({ name: "Test User", email: "test@insightflow.io", password: "Secret@1" });

    expect(apiFetch).toHaveBeenNthCalledWith(1, "/auth/register/", {
      method: "POST",
      body: JSON.stringify({
        email: "test@insightflow.io",
        username: "test",
        password: "Secret@1",
        first_name: "Test",
        last_name: "User",
      }),
    });
  });

  it("auto-logs in after successful registration and returns tokens", async () => {
    const apiFetch = await getApiFetch();
    apiFetch
      .mockResolvedValueOnce({ message: "User registered successfully", user: mockBackendUser })
      .mockResolvedValueOnce({
        message: "Login successful",
        user: mockBackendUser,
        tokens: { access: "acc", refresh: "ref" },
      });

    const result = await register({ name: "Test User", email: "test@insightflow.io", password: "Secret@1" });

    expect(result.access).toBe("acc");
    expect(result.user.name).toBe("Test User");
    expect(apiFetch).toHaveBeenCalledTimes(2);
  });
});

describe("logout", () => {
  beforeEach(() => vi.clearAllMocks());

  it("POSTs the refresh token to /auth/logout/", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({});
    const { getRefreshToken } = await import("@/lib/tokenStorage");
    vi.mocked(getRefreshToken).mockReturnValue("stored-refresh");

    await logout();

    expect(apiFetch).toHaveBeenCalledWith("/auth/logout/", {
      method: "POST",
      body: JSON.stringify({ refresh: "stored-refresh" }),
    });
  });

  it("clears all tokens even when the API call fails", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockRejectedValue(new Error("Network error"));
    const { getRefreshToken, clearAllTokens } = await import("@/lib/tokenStorage");
    vi.mocked(getRefreshToken).mockReturnValue("stored-refresh");

    await logout();

    expect(vi.mocked(clearAllTokens)).toHaveBeenCalled();
  });

  it("skips the API call when no refresh token is stored", async () => {
    const apiFetch = await getApiFetch();
    const { getRefreshToken } = await import("@/lib/tokenStorage");
    vi.mocked(getRefreshToken).mockReturnValue(null);

    await logout();

    expect(apiFetch).not.toHaveBeenCalled();
  });
});

describe("refreshToken", () => {
  it("POSTs to /auth/token/refresh/ with the provided token", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({ access: "new-access" });

    const result = await refreshToken("old-refresh");

    expect(apiFetch).toHaveBeenCalledWith("/auth/token/refresh/", {
      method: "POST",
      body: JSON.stringify({ refresh: "old-refresh" }),
    });
    expect(result.access).toBe("new-access");
  });
});
