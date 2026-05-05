import "server-only";
import type { ApiResult } from "./types";

export const DEFAULT_BACKEND_API_BASE_URL = "http://127.0.0.1:8000/api";

type ApiErrorPayload = string | Record<string, unknown> | null;

export class ApiError extends Error {
  readonly status: number;
  readonly payload: ApiErrorPayload;

  constructor(message: string, status: number, payload: ApiErrorPayload) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

export class ApiConnectionError extends Error {
  readonly cause: unknown;

  constructor(message: string, cause: unknown) {
    super(message);
    this.name = "ApiConnectionError";
    this.cause = cause;
  }
}

export function getBackendApiBaseUrl() {
  const value = process.env.BACKEND_API_BASE_URL?.trim();
  return stripTrailingSlash(value || DEFAULT_BACKEND_API_BASE_URL);
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = `${getBackendApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = new Headers(init.headers);

  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const apiToken = process.env.BACKEND_API_TOKEN?.trim();
  if (apiToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${apiToken}`);
  }

  let response: Response;

  try {
    response = await fetch(url, {
      ...init,
      headers,
      cache: init.cache ?? "no-store",
    });
  } catch (error) {
    throw new ApiConnectionError(`Could not reach backend API at ${url}.`, error);
  }

  const payload = await readPayload(response);

  if (!response.ok) {
    throw new ApiError(getPayloadMessage(payload, response.statusText), response.status, payload);
  }

  return payload as T;
}

export async function toApiResult<T>(request: Promise<T>): Promise<ApiResult<T>> {
  try {
    return { ok: true, data: await request };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error : new Error("Unknown API error"),
    };
  }
}

export function getApiErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return `Backend returned ${error.status}: ${error.message}`;
  }

  if (error instanceof ApiConnectionError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unknown API error";
}

async function readPayload(response: Response): Promise<ApiErrorPayload> {
  const contentType = response.headers.get("content-type");

  if (contentType?.includes("application/json")) {
    try {
      return (await response.json()) as Record<string, unknown>;
    } catch {
      return null;
    }
  }

  try {
    return await response.text();
  } catch {
    return null;
  }
}

function getPayloadMessage(payload: ApiErrorPayload, fallback: string) {
  if (typeof payload === "string" && payload.trim()) {
    return payload.trim();
  }

  if (payload && typeof payload === "object") {
    const error = payload.error;
    if (typeof error === "string" && error.trim()) {
      return error.trim();
    }
  }

  return fallback || "Request failed";
}

function stripTrailingSlash(value: string) {
  return value.replace(/\/+$/, "");
}
