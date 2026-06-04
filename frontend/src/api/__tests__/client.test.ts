import { describe, it, expect, vi, beforeEach } from "vitest";
import { ApiError, apiFetch } from "@/api/client";

vi.mock("@/lib/tokenStorage", () => ({
  getToken: vi.fn(() => null),
}));

describe("ApiError", () => {
  it("carries status and detail", () => {
    const err = new ApiError(400, "Bad request");
    expect(err.status).toBe(400);
    expect(err.detail).toBe("Bad request");
    expect(err.message).toBe("Bad request");
    expect(err).toBeInstanceOf(Error);
  });
});

describe("apiFetch", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("returns parsed JSON on a 2xx response", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ data: "ok" }),
    } as Response);

    const result = await apiFetch<{ data: string }>("/some/path/");
    expect(result).toEqual({ data: "ok" });
  });

  it("throws ApiError with parsed DRF field errors on 4xx", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: async () => ({ email: ["A user with this email already exists."] }),
    } as Response);

    await expect(apiFetch("/auth/register/")).rejects.toMatchObject({
      status: 400,
      detail: "A user with this email already exists.",
    });
  });

  it("throws ApiError with non_field_errors message", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 400,
      statusText: "Bad Request",
      json: async () => ({ non_field_errors: ["Invalid email or password."] }),
    } as Response);

    await expect(apiFetch("/auth/login/")).rejects.toMatchObject({
      detail: "Invalid email or password.",
    });
  });

  it("throws ApiError on 401 without redirecting in non-browser env", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: async () => ({}),
    } as Response);

    await expect(apiFetch("/protected/")).rejects.toMatchObject({
      status: 401,
    });
  });

  it("includes Authorization header when token exists", async () => {
    const { getToken } = await import("@/lib/tokenStorage");
    vi.mocked(getToken).mockReturnValue("my-access-token");

    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    } as Response);

    await apiFetch("/some/path/");

    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect((options?.headers as Record<string, string>)["Authorization"]).toBe(
      "Bearer my-access-token"
    );
  });
});
