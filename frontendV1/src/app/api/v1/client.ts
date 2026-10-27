/**
 * QNU AI v1 API client.
 *
 * This module is the only place allowed to call `fetch` for the v1 screens.
 * The KTX template boundary (`app/api/backend-fetch.ts`) stays closed, so a
 * copied KTX screen can never reach backendV1, the KTX BFF or production KTX.
 */

export type ProblemDetail = {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  /** Stable machine code from `qnu.contracts.problem.ProblemDetail`. */
  code?: string;
  correlation_id?: string | null;
  /** Only present when the backend actually returns per-field errors. */
  errors?: Record<string, string[]>;
};

export type V1ErrorKind =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "invalid"
  | "server"
  | "network"
  | "unexpected";

export class ApiProblemError extends Error {
  readonly status: number;
  readonly code: string;
  readonly correlationId: string | null;
  readonly problem: ProblemDetail | undefined;
  readonly kind: V1ErrorKind;

  constructor(args: {
    status: number;
    message: string;
    code: string;
    correlationId?: string | null;
    problem?: ProblemDetail;
  }) {
    super(args.message);
    this.name = "ApiProblemError";
    this.status = args.status;
    this.code = args.code;
    this.correlationId = args.correlationId ?? null;
    this.problem = args.problem;
    this.kind = classify(args.status);
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** True only when the backend really sent field errors. */
  get fieldErrors(): Record<string, string[]> | undefined {
    const errors = this.problem?.errors;
    return errors && Object.keys(errors).length > 0 ? errors : undefined;
  }
}

function classify(status: number): V1ErrorKind {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  if (status === 409) return "conflict";
  if (status === 422) return "invalid";
  if (status >= 500) return "server";
  if (status === 0) return "network";
  return "unexpected";
}

export type QueryValue = string | number | boolean | null | undefined;

export type BlobResponse = {
  blob: Blob;
  fileName?: string;
  contentType: string;
  size: number;
  etag?: string;
};

export type V1RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  searchParams?: Record<string, QueryValue>;
  signal?: AbortSignal;
  idempotencyKey?: string;
  responseType?: "json" | "blob";
};

export function parseContentDispositionFileName(
  header: string | null | undefined,
): string | undefined {
  if (!header) return undefined;
  const rfc5987Match = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (rfc5987Match?.[1]) {
    try {
      return decodeURIComponent(rfc5987Match[1].trim());
    } catch {
      return rfc5987Match[1].trim();
    }
  }
  const standardMatch = header.match(/filename="?([^";]+)"?/i);
  if (standardMatch?.[1]) {
    return standardMatch[1].trim();
  }
  return undefined;
}

export type V1Client = {
  readonly baseUrl: string;
  readonly prefix: string;
  request: <T>(path: string, options?: V1RequestOptions) => Promise<T>;
  get: <T>(
    path: string,
    options?: Omit<V1RequestOptions, "method" | "body">,
  ) => Promise<T>;
  post: <T>(
    path: string,
    body?: unknown,
    options?: Omit<V1RequestOptions, "method" | "body">,
  ) => Promise<T>;
  put: <T>(
    path: string,
    body?: unknown,
    options?: Omit<V1RequestOptions, "method" | "body">,
  ) => Promise<T>;
  patch: <T>(
    path: string,
    body?: unknown,
    options?: Omit<V1RequestOptions, "method" | "body">,
  ) => Promise<T>;
  delete: <T>(
    path: string,
    options?: Omit<V1RequestOptions, "method" | "body">,
  ) => Promise<T>;
  upload: <T>(
    path: string,
    formData: FormData,
    options?: Omit<V1RequestOptions, "method" | "body">,
  ) => Promise<T>;
  requestBlob: (
    path: string,
    options?: Omit<V1RequestOptions, "responseType">,
  ) => Promise<BlobResponse>;
};

export type V1Fetch = (input: string, init?: RequestInit) => Promise<Response>;

export type V1ClientOptions = {
  baseUrl?: string;
  prefix?: string;
  fetchImpl?: V1Fetch;
  getToken?: () => string | null;
  getAccessToken?: () => string | null;
  getSessionId?: () => number;
  onUnauthorized?: (context?: {
    sessionId?: number;
    expired?: boolean;
  }) => void;
  timeoutMs?: number;
};

export function buildV1Url(
  baseUrl = "",
  prefix = "/platform/v1alpha1",
  path = "",
  searchParams?: Record<string, QueryValue>,
): string {
  const root = baseUrl ? baseUrl.replace(/\/$/, "") : "";
  const cleanPrefix = prefix ? `/${prefix.replace(/^\/+|\/+$/g, "")}` : "";
  const cleanPath = `/${path.replace(/^\/+/, "")}`;
  const url = `${root}${cleanPrefix}${cleanPath}`;
  if (!searchParams) return url;

  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(searchParams)) {
    if (value === undefined || value === null || value === "") continue;
    query.append(key, String(value));
  }
  const queryString = query.toString();
  return queryString ? `${url}?${queryString}` : url;
}

function isJsonResponse(response: Response): boolean {
  const contentType = response.headers.get("content-type") ?? "";
  return (
    contentType.includes("application/json") ||
    contentType.includes("application/problem+json")
  );
}

function asProblem(value: unknown): ProblemDetail | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value))
    return undefined;
  return value as ProblemDetail;
}

function problemMessage(problem: ProblemDetail | undefined, status: number) {
  return (
    problem?.detail ??
    problem?.title ??
    `Yêu cầu thất bại (${status}). Vui lòng thử lại.`
  );
}

export function createV1Client(options: V1ClientOptions = {}): V1Client {
  const {
    baseUrl = "",
    prefix = "/platform/v1alpha1",
    fetchImpl,
    getToken,
    getAccessToken,
    getSessionId,
    onUnauthorized,
    timeoutMs = 30_000,
  } = options;

  const resolveToken = getToken ?? getAccessToken;

  async function request<T>(
    path: string,
    requestOptions: V1RequestOptions = {},
  ): Promise<T> {
    const {
      method = "GET",
      body,
      headers: customHeaders,
      searchParams,
      signal,
      idempotencyKey,
      responseType = "json",
    } = requestOptions;
    const startingSessionId = getSessionId?.() ?? 0;
    const headers = new Headers();
    if (responseType === "blob") {
      headers.set("Accept", "*/*");
    } else {
      headers.set("Accept", "application/json");
    }
    const token = resolveToken?.() ?? null;
    if (token) headers.set("Authorization", `Bearer ${token}`);

    if (idempotencyKey) {
      headers.set("Idempotency-Key", idempotencyKey);
    }

    if (customHeaders) {
      for (const [key, value] of Object.entries(customHeaders)) {
        if (value !== undefined) headers.set(key, value);
      }
    }

    let payload: BodyInit | undefined;
    if (body !== undefined) {
      if (typeof FormData !== "undefined" && body instanceof FormData) {
        // Do NOT set Content-Type header: browser must generate multipart/form-data with boundary
        payload = body;
      } else {
        headers.set("Content-Type", "application/json");
        payload = JSON.stringify(body);
      }
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const abort = () => controller.abort();
    signal?.addEventListener("abort", abort);

    let response: Response;
    try {
      response = await (fetchImpl ?? globalThis.fetch)(
        buildV1Url(baseUrl, prefix, path, searchParams),
        {
          method,
          headers,
          body: payload,
          // Bearer only: never attach KTX/BFF cookies to a v1 call.
          credentials: "omit",
          cache: "no-store",
          redirect: "error",
          signal: controller.signal,
        },
      );
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        throw new ApiProblemError({
          status: 0,
          code: "request_aborted",
          message: "Yêu cầu đã bị hủy hoặc quá thời gian chờ.",
        });
      }
      throw new ApiProblemError({
        status: 0,
        code: "network_unreachable",
        message:
          "Không kết nối được backendV1. Kiểm tra dịch vụ đang chạy ở cổng 8002.",
      });
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", abort);
    }

    if (getSessionId && getSessionId() !== startingSessionId) {
      throw new ApiProblemError({
        status: 0,
        code: "session_aborted",
        message: "Phiên làm việc đã thay đổi trong khi yêu cầu đang thực hiện.",
      });
    }

    if (!response.ok) {
      const parsed = isJsonResponse(response)
        ? await response.json()
        : undefined;
      const problem = asProblem(parsed);
      if (response.status === 401) {
        onUnauthorized?.({ sessionId: startingSessionId });
      }
      throw new ApiProblemError({
        status: response.status,
        message: problemMessage(problem, response.status),
        code: problem?.code ?? `http_${response.status}`,
        correlationId: problem?.correlation_id ?? null,
        problem,
      });
    }

    if (responseType === "blob") {
      const blob = await response.blob();
      const contentDisposition = response.headers.get("content-disposition");
      const contentType =
        response.headers.get("content-type") ||
        blob.type ||
        "application/octet-stream";
      const etag = response.headers.get("etag") ?? undefined;
      const fileName = parseContentDispositionFileName(contentDisposition);
      return {
        blob,
        fileName,
        contentType,
        size: blob.size,
        etag,
      } as T;
    }

    const parsed = isJsonResponse(response) ? await response.json() : undefined;
    return parsed as T;
  }

  return {
    baseUrl,
    prefix,
    request,
    get: (path, requestOptions) =>
      request(path, { ...requestOptions, method: "GET" }),
    post: (path, body, requestOptions) =>
      request(path, { ...requestOptions, method: "POST", body }),
    put: (path, body, requestOptions) =>
      request(path, { ...requestOptions, method: "PUT", body }),
    patch: (path, body, requestOptions) =>
      request(path, { ...requestOptions, method: "PATCH", body }),
    delete: (path, requestOptions) =>
      request(path, { ...requestOptions, method: "DELETE" }),
    upload: (path, formData, requestOptions) =>
      request(path, { ...requestOptions, method: "POST", body: formData }),
    requestBlob: (path, requestOptions) =>
      request<BlobResponse>(path, {
        ...requestOptions,
        method: "GET",
        responseType: "blob",
      }),
  };
}
