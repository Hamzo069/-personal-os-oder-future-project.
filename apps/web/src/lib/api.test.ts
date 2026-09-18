import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, refreshSession, setAccessToken, setSessionExpiredHandler } from "@/lib/api";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

describe("api client", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
    setAccessToken(null);
    setSessionExpiredHandler(null);
  });

  afterEach(() => vi.unstubAllGlobals());

  it("sends the bearer token and parses JSON", async () => {
    setAccessToken("token-1");
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { id: "u1" }));
    const result = await api.get<{ id: string }>("/auth/me");
    expect(result).toEqual({ id: "u1" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/auth/me");
    expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer token-1");
    expect(init?.credentials).toBe("include");
  });

  it("refreshes once on 401 and retries the request with the new token", async () => {
    setAccessToken("expired");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { error: { code: "unauthorized", message: "expired" } }))
      .mockResolvedValueOnce(jsonResponse(200, { access_token: "fresh", token_type: "bearer", expires_in: 900 }))
      .mockResolvedValueOnce(jsonResponse(200, { items: [] }));

    const result = await api.get<{ items: unknown[] }>("/transactions");
    expect(result).toEqual({ items: [] });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/auth/refresh");
    const retryHeaders = fetchMock.mock.calls[2][1]?.headers as Record<string, string>;
    expect(retryHeaders.Authorization).toBe("Bearer fresh");
  });

  it("calls the session-expired handler when refresh fails", async () => {
    const expired = vi.fn();
    setSessionExpiredHandler(expired);
    setAccessToken("expired");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { error: { code: "unauthorized", message: "expired" } }))
      .mockResolvedValueOnce(jsonResponse(401, { error: { code: "unauthorized", message: "no cookie" } }));

    await expect(api.get("/transactions")).rejects.toBeInstanceOf(ApiError);
    expect(expired).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("shares one in-flight refresh between concurrent callers", async () => {
    let resolveRefresh: (value: Response) => void = () => {};
    fetchMock.mockImplementationOnce(() => new Promise<Response>((resolve) => (resolveRefresh = resolve)));
    const first = refreshSession();
    const second = refreshSession();
    resolveRefresh(jsonResponse(200, { access_token: "shared", token_type: "bearer", expires_in: 900 }));
    expect(await Promise.all([first, second])).toEqual([true, true]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("exposes the error envelope as ApiError", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(422, { error: { code: "validation_error", message: "Request validation failed", details: [{ loc: ["amount"] }] } }),
    );
    const error = await api.post("/transactions", {}).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(422);
    expect((error as ApiError).code).toBe("validation_error");
    expect((error as ApiError).details).toEqual([{ loc: ["amount"] }]);
  });

  it("drops empty query parameters", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {}));
    await api.get("/transactions", { q: "", page: 2, category_id: undefined, sort: "date_desc" });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/transactions?page=2&sort=date_desc");
  });
});
