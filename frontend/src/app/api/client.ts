import { runtimeConfig } from "@/app/config/runtime";

export type ProblemDetails = {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  errors?: Record<string, string[]>;
};

export class ApiError extends Error {
  readonly status: number;
  readonly problemDetails?: ProblemDetails;

  constructor(
    status: number,
    message: string,
    problemDetails?: ProblemDetails,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.problemDetails = problemDetails;
  }

  get fieldErrors(): Record<string, string[]> | undefined {
    return this.problemDetails?.errors;
  }
}

export type QueryValue = string | number | boolean | null | undefined;

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: BodyInit | unknown;
  searchParams?: Record<string, QueryValue | QueryValue[]>;
};

function joinUrl(
  baseUrl: string,
  path: string,
  searchParams?: Record<string, QueryValue | QueryValue[]>,
): string {
  const joinedPath = /^https?:\/\//i.test(path)
    ? path
    : `${baseUrl.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
  if (!searchParams) return joinedPath;

  const [pathWithoutHash, hash = ""] = joinedPath.split("#", 2);
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(searchParams)) {
    const values = Array.isArray(value) ? value : [value];
    for (const item of values) {
      if (item !== undefined && item !== null && item !== "") {
        query.append(key, String(item));
      }
    }
  }
  const queryString = query.toString();
  if (!queryString) return joinedPath;
  const separator = pathWithoutHash.includes("?") ? "&" : "?";
  return `${pathWithoutHash}${separator}${queryString}${hash ? `#${hash}` : ""}`;
}

async function readResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined;

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  return text || undefined;
}

function toProblemDetails(body: unknown): ProblemDetails | undefined {
  if (!body || typeof body !== "object" || Array.isArray(body))
    return undefined;
  return body as ProblemDetails;
}

function getErrorMessage(status: number, body: unknown): string {
  const problemDetails = toProblemDetails(body);
  if (problemDetails?.errors) {
    const errorEntries = Object.values(problemDetails.errors);
    for (const messages of errorEntries) {
      if (
        Array.isArray(messages) &&
        messages.length > 0 &&
        typeof messages[0] === "string"
      ) {
        return messages[0];
      }
    }
  }
  return (
    problemDetails?.detail ??
    problemDetails?.title ??
    (typeof body === "string" ? body : undefined) ??
    `Yêu cầu thất bại (${status}).`
  );
}

export function createApiClient(baseUrl: string) {
  async function request<T>(
    path: string,
    options: RequestOptions = {},
  ): Promise<T> {
    const { searchParams, ...requestOptions } = options;
    const headers = new Headers(requestOptions.headers);
    const isFormData = requestOptions.body instanceof FormData;
    let body: BodyInit | undefined;

    if (requestOptions.body !== undefined) {
      if (
        typeof requestOptions.body === "string" ||
        requestOptions.body instanceof FormData ||
        requestOptions.body instanceof Blob ||
        requestOptions.body instanceof ArrayBuffer
      ) {
        body = requestOptions.body;
      } else {
        headers.set("Content-Type", "application/json");
        body = JSON.stringify(requestOptions.body);
      }
    }

    if (!isFormData && body !== undefined && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const response = await fetch(joinUrl(baseUrl, path, searchParams), {
      ...requestOptions,
      body,
      credentials: "include",
      headers,
    });
    const responseBody = await readResponseBody(response);

    if (!response.ok) {
      const problemDetails = toProblemDetails(responseBody);
      throw new ApiError(
        response.status,
        getErrorMessage(response.status, responseBody),
        problemDetails,
      );
    }

    return responseBody as T;
  }

  return {
    request,
    get: <T>(path: string, options?: Omit<RequestOptions, "method" | "body">) =>
      request<T>(path, { ...options, method: "GET" }),
    post: <T>(
      path: string,
      body?: unknown,
      options?: Omit<RequestOptions, "method" | "body">,
    ) => request<T>(path, { ...options, method: "POST", body }),
    put: <T>(
      path: string,
      body?: unknown,
      options?: Omit<RequestOptions, "method" | "body">,
    ) => request<T>(path, { ...options, method: "PUT", body }),
    patch: <T>(
      path: string,
      body?: unknown,
      options?: Omit<RequestOptions, "method" | "body">,
    ) => request<T>(path, { ...options, method: "PATCH", body }),
    delete: <T>(
      path: string,
      options?: Omit<RequestOptions, "method" | "body">,
    ) => request<T>(path, { ...options, method: "DELETE" }),
  };
}

export const apiClient = createApiClient(runtimeConfig.apiBaseUrl);
export const bffClient = createApiClient(runtimeConfig.bffBaseUrl);
