import type {
  ApprovalIn,
  AnalyticsOverview,
  Audit,
  AuditEvent,
  AuditIn,
  ApprovedFact,
  BrandRuleIn,
  Document,
  FactIn,
  Finding,
  FindingStatus,
  HealthResponse,
  RevisionIn,
  TermIn,
  Terminology,
  Workspace,
  WorkspaceIn,
} from "@/types/api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function buildUrl(
  path: string,
  params?: Record<string, string | number | undefined>,
) {
  const url = new URL(`${API_BASE}${path}`);

  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined) {
      url.searchParams.set(key, String(value));
    }
  });

  return url.toString();
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(buildUrl(path, params), {
      ...options,
      headers: {
        ...(options.body instanceof FormData
          ? {}
          : { "Content-Type": "application/json" }),
        ...options.headers,
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "Unable to reach the INKGUARD backend. Check that the API server is running.",
      0,
    );
  }

  const text = await response.text();
  let data: unknown = null;

  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!response.ok) {
    const message =
      typeof data === "object" &&
      data !== null &&
      "detail" in data
        ? String(data.detail)
        : `API request failed (${response.status})`;

    throw new ApiError(message, response.status, data);
  }

  return data as T;
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  health: () =>
    request<HealthResponse>("/api/health"),

  workspaces: {
    list: () =>
      request<Workspace[]>("/api/workspaces"),

    get: (id: string) =>
      request<Workspace>(`/api/workspaces/${id}`),

    create: (input: WorkspaceIn) =>
      request<Workspace>("/api/workspaces", json("POST", input)),
  },

  documents: {
    list: (workspaceId: string) =>
      request<Document[]>("/api/documents", {}, {
        workspace_id: workspaceId,
      }),

    upload: (
      workspaceId: string,
      file: File,
      kind = "submission",
    ) => {
      const form = new FormData();
      form.append("file", file);

      return request<Document>(
        "/api/documents/upload",
        { method: "POST", body: form },
        { workspace_id: workspaceId, kind },
      );
    },

    get: (id: string) =>
      request<unknown>(`/api/documents/${id}`),
  },

  brand: {
    rules: (workspaceId: string) =>
      request<unknown[]>("/api/brand/rules", {}, {
        workspace_id: workspaceId,
      }),

    createRule: (input: BrandRuleIn) =>
      request<unknown>("/api/brand/rules", json("POST", input)),

    facts: (workspaceId: string) =>
      request<ApprovedFact[]>("/api/brand/facts", {}, {
        workspace_id: workspaceId,
      }),

    createFact: (input: FactIn) =>
      request<ApprovedFact>("/api/brand/facts", json("POST", input)),

    terminology: (workspaceId: string) =>
      request<Terminology[]>("/api/brand/terminology", {}, {
        workspace_id: workspaceId,
      }),

    createTerm: (input: TermIn) =>
      request<Terminology>("/api/brand/terminology", json("POST", input)),
  },

  audits: {
    list: (workspaceId: string) =>
      request<unknown[]>("/api/audits", {}, {
        workspace_id: workspaceId,
      }),

    get: (id: string) =>
      request<Audit>(`/api/audits/${id}`),

    create: (input: AuditIn) =>
      request<Audit>("/api/audits", json("POST", input)),

    createRevision: (id: string, input: RevisionIn) =>
      request<unknown>(
        `/api/audits/${id}/revisions`,
        json("POST", input),
      ),

    reevaluate: (id: string) =>
      request<Audit>(
        `/api/audits/${id}/reevaluate`,
        json("POST"),
      ),

    approve: (id: string, input: ApprovalIn) =>
      request<Audit>(
        `/api/audits/${id}/approve`,
        json("POST", input),
      ),

    events: (id: string) =>
      request<AuditEvent[]>(`/api/audits/${id}/events`),
  },

  findings: {
    setStatus: (id: string, status: FindingStatus) =>
      request<Finding>(
        `/api/findings/${id}`,
        { method: "PATCH" },
        { status },
      ),
  },

  analytics: {
    overview: (workspaceId: string) =>
      request<AnalyticsOverview>("/api/analytics/overview", {}, {
        workspace_id: workspaceId,
      }),
  },

  events: {
    list: (workspaceId: string, limit = 10) =>
      request<AuditEvent[]>("/api/events", {}, {
        workspace_id: workspaceId,
        limit,
      }),
  },
};