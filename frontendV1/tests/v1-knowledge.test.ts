/**
 * Contract and regression tests for Knowledge domain (Collections, Sources, Revisions).
 */

import assert from "node:assert/strict";
import { test } from "vitest";
import {
  ApiProblemError,
  createV1Client,
  parseContentDispositionFileName,
} from "../src/app/api/v1/client.ts";
import { canManageKnowledge } from "../src/features/knowledge/permissions.ts";
import { knowledgeKeys } from "../src/features/knowledge/queries.ts";
import {
  addRevision,
  createCollection,
  downloadRevisionContent,
  getCollection,
  getSource,
  listCollections,
  listRevisions,
  listSources,
  updateCollection,
  uploadSource,
} from "../src/features/knowledge/requests.ts";
import {
  formatBytes,
  formatSourceStatus,
  generateIdempotencyKey,
  isDocx,
  isPdf,
  validateUploadFile,
} from "../src/features/knowledge/schemas.ts";

type RecordedCall = {
  url: string;
  method: string;
  headers: Headers;
  body: unknown;
};

function createMockFetch(
  handler: (call: RecordedCall) => Response | Promise<Response>,
) {
  const calls: RecordedCall[] = [];
  const fetchImpl = async (input: string, init?: RequestInit) => {
    const call: RecordedCall = {
      url: input,
      method: init?.method ?? "GET",
      headers: new Headers(init?.headers),
      body: init?.body,
    };
    calls.push(call);
    return handler(call);
  };
  return { calls, fetchImpl };
}

test("Knowledge API: Collections list, create, get, and partial update contract", async () => {
  const { calls, fetchImpl } = createMockFetch((call) => {
    if (call.method === "GET" && call.url.includes("/collections?")) {
      return new Response(
        JSON.stringify({
          items: [
            {
              id: "col-1",
              workspace_id: "ws-1",
              name: "Tuyển sinh 2026",
              description: "Hồ sơ tuyển sinh",
              source_count: 5,
              created_by: "actor-admin",
              created_at: "2026-10-27T08:00:00Z",
              updated_at: "2026-10-27T08:00:00Z",
            },
          ],
          meta: { page: 1, page_size: 20, total: 1 },
        }),
        { headers: { "Content-Type": "application/json" }, status: 200 },
      );
    }
    if (call.method === "POST" && call.url.endsWith("/collections")) {
      return new Response(
        JSON.stringify({
          id: "col-new",
          workspace_id: "ws-1",
          name: "Bộ sưu tập mới",
          description: null,
          source_count: 0,
          created_by: "actor-admin",
          created_at: "2026-10-27T08:05:00Z",
          updated_at: "2026-10-27T08:05:00Z",
        }),
        { headers: { "Content-Type": "application/json" }, status: 201 },
      );
    }
    if (call.method === "PATCH" && call.url.includes("/collections/col-1")) {
      return new Response(
        JSON.stringify({
          id: "col-1",
          workspace_id: "ws-1",
          name: "Tên mới",
          description: null,
          source_count: 5,
          created_by: "actor-admin",
          created_at: "2026-10-27T08:00:00Z",
          updated_at: "2026-10-27T08:10:00Z",
        }),
        { headers: { "Content-Type": "application/json" }, status: 200 },
      );
    }
    return new Response(null, { status: 404 });
  });

  const client = createV1Client({
    fetchImpl,
    getToken: () => "mock_token",
  });

  // 1. List collections
  const listResult = await listCollections(client, "ws-1", {
    page: 2,
    pageSize: 10,
  });
  assert.equal(listResult.items.length, 1);
  assert.equal(listResult.meta.total, 1);
  assert.equal(calls[0].method, "GET");
  assert.match(
    calls[0].url,
    /\/workspaces\/ws-1\/collections\?page=2&page_size=10/,
  );

  // 2. Create collection
  const created = await createCollection(client, "ws-1", {
    name: "Bộ sưu tập mới",
    description: "",
  });
  assert.equal(created.id, "col-new");
  assert.equal(calls[1].method, "POST");
  assert.match(calls[1].url, /\/workspaces\/ws-1\/collections$/);
  assert.equal(calls[1].headers.get("content-type"), "application/json");

  // 3. Update collection: explicit null description to clear
  const updated = await updateCollection(client, "ws-1", "col-1", {
    name: "Tên mới",
    description: null,
  });
  assert.equal(updated.name, "Tên mới");
  assert.equal(calls[2].method, "PATCH");
  const patchPayload = JSON.parse(calls[2].body as string);
  assert.deepEqual(patchPayload, { name: "Tên mới", description: null });

  // 4. Update collection: omission keeps description
  await updateCollection(client, "ws-1", "col-1", {
    name: "Tên khác",
  });
  const keepPayload = JSON.parse(calls[3].body as string);
  assert.deepEqual(keepPayload, { name: "Tên khác" });
  assert.equal("description" in keepPayload, false);
});

test("Knowledge API: Source upload sends multipart FormData without JSON header and includes Idempotency-Key", async () => {
  let capturedCall: RecordedCall | null = null;
  const { fetchImpl } = createMockFetch((call) => {
    capturedCall = call;
    return new Response(
      JSON.stringify({
        source: {
          id: "src-1",
          workspace_id: "ws-1",
          collection_id: "col-1",
          title: "Tài liệu mẫu",
          status: "stored",
          revision_count: 1,
          current_revision_no: 1,
          file_name: "sample.pdf",
          content_type: "application/pdf",
          size_bytes: 1024,
          sha256: "abcd".repeat(16),
          created_by: "actor-editor",
          created_at: "2026-10-27T08:00:00Z",
          updated_at: "2026-10-27T08:00:00Z",
        },
        revision: {
          id: "rev-1",
          source_id: "src-1",
          revision_no: 1,
          file_name: "sample.pdf",
          content_type: "application/pdf",
          size_bytes: 1024,
          sha256: "abcd".repeat(16),
          created_by: "actor-editor",
          created_at: "2026-10-27T08:00:00Z",
        },
      }),
      { headers: { "Content-Type": "application/json" }, status: 201 },
    );
  });

  const client = createV1Client({
    fetchImpl,
    getToken: () => "mock_token",
  });

  const dummyPdf = new File(
    [new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d])],
    "sample.pdf",
    {
      type: "application/pdf",
    },
  );
  const testKey = "qnu-up-test-key-12345678";

  const result = await uploadSource(
    client,
    "ws-1",
    "col-1",
    dummyPdf,
    "Tài liệu mẫu",
    testKey,
  );

  assert.equal(result.source.id, "src-1");
  assert.equal(result.revision.revision_no, 1);
  assert.ok(capturedCall);
  assert.equal(capturedCall.method, "POST");
  assert.match(
    capturedCall.url,
    /\/workspaces\/ws-1\/collections\/col-1\/sources$/,
  );

  // CRITICAL: Content-Type must NOT be application/json; browser/runtime sets multipart
  assert.notEqual(capturedCall.headers.get("content-type"), "application/json");
  // Idempotency-Key header is present
  assert.equal(capturedCall.headers.get("idempotency-key"), testKey);

  // FormData carries file and title
  const body = capturedCall.body as FormData;
  assert.ok(body instanceof FormData);
  assert.ok(body.get("file"));
  assert.equal(body.get("title"), "Tài liệu mẫu");
});

test("Knowledge API: Revision upload strictly omits title from FormData", async () => {
  let capturedCall: RecordedCall | null = null;
  const { fetchImpl } = createMockFetch((call) => {
    capturedCall = call;
    return new Response(
      JSON.stringify({
        source: {
          id: "src-1",
          workspace_id: "ws-1",
          collection_id: "col-1",
          title: "Tài liệu gốc",
          status: "stored",
          revision_count: 2,
          current_revision_no: 2,
          file_name: "v2.pdf",
          content_type: "application/pdf",
          size_bytes: 2048,
          sha256: "1234".repeat(16),
          created_by: "actor-editor",
          created_at: "2026-10-27T08:00:00Z",
          updated_at: "2026-10-27T08:15:00Z",
        },
        revision: {
          id: "rev-2",
          source_id: "src-1",
          revision_no: 2,
          file_name: "v2.pdf",
          content_type: "application/pdf",
          size_bytes: 2048,
          sha256: "1234".repeat(16),
          created_by: "actor-editor",
          created_at: "2026-10-27T08:15:00Z",
        },
      }),
      { headers: { "Content-Type": "application/json" }, status: 201 },
    );
  });

  const client = createV1Client({
    fetchImpl,
    getToken: () => "mock_token",
  });

  const dummyPdfV2 = new File(
    [new Uint8Array([0x25, 0x50, 0x44, 0x46])],
    "v2.pdf",
    {
      type: "application/pdf",
    },
  );
  const revKey = "qnu-up-rev-key-87654321";

  const result = await addRevision(
    client,
    "ws-1",
    "col-1",
    "src-1",
    dummyPdfV2,
    revKey,
  );

  assert.equal(result.revision.revision_no, 2);
  assert.ok(capturedCall);
  assert.equal(capturedCall.method, "POST");
  assert.match(
    capturedCall.url,
    /\/workspaces\/ws-1\/collections\/col-1\/sources\/src-1\/revisions$/,
  );

  const body = capturedCall.body as FormData;
  assert.ok(body.get("file"));
  // Backend forbids "title" in revision upload (code 422 revision_title_not_supported)
  assert.equal(body.get("title"), null);
  assert.equal(capturedCall.headers.get("idempotency-key"), revKey);
});

test("Knowledge API: Binary download returns Blob with parsed filename, and HTTP errors throw ApiProblemError", async () => {
  const binaryPayload = new Uint8Array([
    0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x37,
  ]);
  const { calls, fetchImpl } = createMockFetch((call) => {
    if (call.url.includes("/revisions/rev-1/content")) {
      return new Response(binaryPayload, {
        status: 200,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition":
            "attachment; filename*=UTF-8''Quy%20ch%E1%BA%BF%202026.pdf",
          ETag: '"abcd1234"',
        },
      });
    }
    if (call.url.includes("/revisions/rev-missing/content")) {
      return new Response(
        JSON.stringify({
          type: "https://errors.qnu.edu.vn/not_found",
          title: "Không tìm thấy phiên bản tài liệu.",
          status: 404,
          code: "revision_not_found",
          correlation_id: "corr-404-test",
        }),
        {
          status: 404,
          headers: { "Content-Type": "application/problem+json" },
        },
      );
    }
    return new Response(null, { status: 500 });
  });

  const client = createV1Client({
    fetchImpl,
    getToken: () => "mock_token",
  });

  // 1. Successful binary download
  const blobRes = await downloadRevisionContent(
    client,
    "ws-1",
    "col-1",
    "src-1",
    "rev-1",
  );
  assert.equal(blobRes.fileName, "Quy chế 2026.pdf");
  assert.equal(blobRes.contentType, "application/pdf");
  assert.equal(blobRes.etag, '"abcd1234"');
  assert.equal(blobRes.size, binaryPayload.length);
  assert.equal(calls[0].headers.get("authorization"), "Bearer mock_token");

  // 2. Error response with problem+json must NOT be returned as a downloaded blob!
  await assert.rejects(
    async () => {
      await downloadRevisionContent(
        client,
        "ws-1",
        "col-1",
        "src-1",
        "rev-missing",
      );
    },
    (error: unknown) => {
      assert.ok(error instanceof ApiProblemError);
      assert.equal(error.status, 404);
      assert.equal(error.code, "revision_not_found");
      assert.equal(error.correlationId, "corr-404-test");
      return true;
    },
  );
});

test("Knowledge Schemas: Idempotency-Key validation, file size checks, and status formatting", () => {
  // 1. Idempotency Key length between 8 and 128 characters
  const key1 = generateIdempotencyKey();
  const key2 = generateIdempotencyKey("test-prefix");
  assert.ok(key1.length >= 8 && key1.length <= 128);
  assert.ok(key2.length >= 8 && key2.length <= 128);
  assert.notEqual(key1, key2);

  // 2. File validation
  assert.equal(validateUploadFile(null), "Vui lòng chọn một tệp.");

  const emptyFile = new File([], "empty.pdf", { type: "application/pdf" });
  assert.equal(validateUploadFile(emptyFile), "Tệp rỗng không được chấp nhận.");

  const exeFile = new File([new Uint8Array([1, 2, 3])], "danger.exe", {
    type: "application/x-msdownload",
  });
  assert.equal(
    validateUploadFile(exeFile),
    "Chỉ hỗ trợ tệp định dạng PDF (.pdf) hoặc Word (.docx).",
  );

  const validPdf = new File([new Uint8Array([1, 2, 3])], "document.pdf", {
    type: "application/pdf",
  });
  assert.equal(validateUploadFile(validPdf), null);

  const validDocx = new File([new Uint8Array([1, 2, 3])], "guide.docx", {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
  assert.equal(validateUploadFile(validDocx), null);

  // 3. Format helpers
  assert.equal(formatSourceStatus("stored"), "Đã lưu tệp");
  assert.equal(formatBytes(1024), "1.0 KB");
  assert.equal(formatBytes(1048576), "1.0 MB");
  assert.equal(isPdf("application/pdf"), true);
  assert.equal(isPdf(undefined, "report.pdf"), true);
  assert.equal(isDocx(undefined, "document.docx"), true);

  // 4. Content-Disposition parsing
  assert.equal(
    parseContentDispositionFileName(
      "attachment; filename*=UTF-8''H%C6%B0%E1%BB%9Bng%20d%E1%BA%ABn.pdf",
    ),
    "Hướng dẫn.pdf",
  );
  assert.equal(
    parseContentDispositionFileName('attachment; filename="simple.docx"'),
    "simple.docx",
  );
});

test("Knowledge Permissions & Query Scoping: admin/editor can write, member is read-only, keys include sessionId", () => {
  // 1. Role checks
  assert.equal(
    canManageKnowledge({ kind: "member", role: "admin", status: "active" }),
    true,
  );
  assert.equal(
    canManageKnowledge({ kind: "member", role: "editor", status: "active" }),
    true,
  );
  assert.equal(
    canManageKnowledge({ kind: "member", role: "reviewer", status: "active" }),
    false,
  );
  assert.equal(
    canManageKnowledge({ kind: "member", role: "member", status: "active" }),
    false,
  );
  assert.equal(canManageKnowledge({ kind: "platform-admin" }), true);
  assert.equal(canManageKnowledge({ kind: "none" }), false);
  assert.equal(canManageKnowledge({ kind: "unknown" }), false);

  // 2. Query keys scoping: sessionId and workspaceId isolation
  const keySession1 = knowledgeKeys.collections(101, "ws-alpha", {
    page: 1,
    pageSize: 20,
  });
  const keySession2 = knowledgeKeys.collections(102, "ws-alpha", {
    page: 1,
    pageSize: 20,
  });
  const keyWsBeta = knowledgeKeys.collections(101, "ws-beta", {
    page: 1,
    pageSize: 20,
  });

  assert.notDeepEqual(keySession1, keySession2);
  assert.notDeepEqual(keySession1, keyWsBeta);
  assert.deepEqual(keySession1, [
    "v1",
    101,
    "workspaces",
    "ws-alpha",
    "knowledge",
    "collections",
    1,
    20,
  ]);
});

test("Knowledge API: Read detail endpoints (getCollection, getSource, listSources, listRevisions)", async () => {
  const { calls, fetchImpl } = createMockFetch((call) => {
    if (call.url.includes("/collections/col-1/sources/src-1/revisions")) {
      return new Response(
        JSON.stringify([
          {
            id: "rev-2",
            source_id: "src-1",
            revision_no: 2,
            file_name: "v2.pdf",
            content_type: "application/pdf",
            size_bytes: 200,
            sha256: "abc2",
            created_by: "actor-1",
            created_at: "2026-10-27T08:10:00Z",
          },
        ]),
        { headers: { "Content-Type": "application/json" }, status: 200 },
      );
    }
    if (call.url.includes("/collections/col-1/sources/src-1")) {
      return new Response(
        JSON.stringify({
          id: "src-1",
          workspace_id: "ws-1",
          collection_id: "col-1",
          title: "Tài liệu",
          status: "stored",
          revision_count: 2,
          current_revision_no: 2,
          file_name: "v2.pdf",
          content_type: "application/pdf",
          size_bytes: 200,
          sha256: "abc2",
          created_by: "actor-1",
          created_at: "2026-10-27T08:00:00Z",
          updated_at: "2026-10-27T08:10:00Z",
        }),
        { headers: { "Content-Type": "application/json" }, status: 200 },
      );
    }
    if (call.url.includes("/collections/col-1/sources?")) {
      return new Response(
        JSON.stringify({
          items: [],
          meta: { page: 1, page_size: 20, total: 0 },
        }),
        { headers: { "Content-Type": "application/json" }, status: 200 },
      );
    }
    if (call.url.includes("/collections/col-1")) {
      return new Response(
        JSON.stringify({
          id: "col-1",
          workspace_id: "ws-1",
          name: "Bộ sưu tập",
          description: "Mô tả",
          source_count: 1,
          created_by: "actor-1",
          created_at: "2026-10-27T08:00:00Z",
          updated_at: "2026-10-27T08:00:00Z",
        }),
        { headers: { "Content-Type": "application/json" }, status: 200 },
      );
    }
    return new Response(null, { status: 404 });
  });

  const client = createV1Client({ fetchImpl, getToken: () => "mock_token" });

  const col = await getCollection(client, "ws-1", "col-1");
  assert.equal(col.name, "Bộ sưu tập");

  const sourcesPage = await listSources(client, "ws-1", "col-1", {
    page: 1,
    pageSize: 20,
  });
  assert.equal(sourcesPage.items.length, 0);

  const src = await getSource(client, "ws-1", "col-1", "src-1");
  assert.equal(src.title, "Tài liệu");

  const revs = await listRevisions(client, "ws-1", "col-1", "src-1");
  assert.equal(revs.length, 1);
  assert.equal(revs[0].revision_no, 2);

  assert.equal(calls.length, 4);
});
