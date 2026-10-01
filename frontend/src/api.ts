// The only module that talks HTTP. Errors arrive as {"error":{"code","message"}} (app_spec §7).

let authToken: string | null = null;

export function setToken(token: string | null): void {
  authToken = token;
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }

  toString(): string {
    return `${this.code}: ${this.message}`;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  const resp = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = resp.status === 204 ? null : await resp.json().catch(() => null);
  if (!resp.ok) {
    const err = data?.error ?? {};
    // VALIDATION_ERROR carries per-field messages; show the first one instead of a generic sentence.
    const fieldMsg = Array.isArray(err.details) && err.details[0]?.msg ? ` (${err.details[0].msg})` : "";
    throw new ApiError(resp.status, err.code ?? "HTTP_ERROR", `${err.message ?? resp.statusText}${fieldMsg}`);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body: unknown = {}) => request<T>("POST", path, body),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
};

export function errorText(err: unknown): string {
  return err instanceof ApiError ? err.toString() : "Unexpected error, please retry";
}
