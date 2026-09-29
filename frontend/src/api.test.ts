import { afterEach, expect, it, vi } from "vitest";
import { ApiError, getJson, request } from "./api";

afterEach(() => vi.unstubAllGlobals());

it("does not treat HTTP failure as successful JSON", async () => {
  const fetch = vi.fn().mockResolvedValue(new Response("{}", { status: 503 }));
  vi.stubGlobal("fetch", fetch);
  await expect(getJson("/health/ready")).rejects.toThrow("HTTP 503");
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("propagates network failures without automatic retries", async () => {
  const fetch = vi.fn().mockRejectedValue(new TypeError("Network error"));
  vi.stubGlobal("fetch", fetch);
  await expect(getJson("/api/v1/status")).rejects.toThrow("Network error");
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("preserves conflict details and does not retry a failed issue", async () => {
  const fetch = vi.fn().mockResolvedValue(
    new Response(
      JSON.stringify({
        error: {
          code: "equipment_already_assigned",
          message: "Оборудование уже выдано",
          details: [],
        },
        request_id: "test-id",
      }),
      { status: 409 },
    ),
  );
  vi.stubGlobal("fetch", fetch);
  await expect(
    request("assignments", "POST", { equipment_id: 1, employee_id: 2 }),
  ).rejects.toMatchObject({
    status: 409,
    message: "Оборудование уже выдано",
    requestId: "test-id",
  } satisfies Partial<ApiError>);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("does not repeat an issue when its network result is unknown", async () => {
  const fetch = vi.fn().mockRejectedValue(new TypeError("Connection lost"));
  vi.stubGlobal("fetch", fetch);
  await expect(
    request("assignments", "POST", { equipment_id: 1, employee_id: 2 }),
  ).rejects.toThrow("Connection lost");
  expect(fetch).toHaveBeenCalledTimes(1);
});
