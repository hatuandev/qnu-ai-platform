// Isolated browser regression: no application DB, model or publication writes.
// Run from frontendV2: node --test tests/studio-browser.mjs
import assert from "node:assert/strict";
import { mkdir, readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { after, before, test } from "node:test";
import { createServer } from "vite";

const require = createRequire(import.meta.url);
const { chromium } = require("../../frontendV1/node_modules/playwright");
let server, browser, url;
const html = `<html lang="vi"><head><meta name="viewport" content="width=device-width,initial-scale=1" /></head><body style="margin:0"><div id="probe" style="height:90vh;width:100%"></div><script type="module">
import React from 'react';
import { createRoot } from 'react-dom/client';
import JSZip from 'jszip';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DocxViewer } from '/src/components/knowledge/docx-viewer.tsx';
import { PublicationDialog } from '/src/components/knowledge/publication-dialog.tsx';
import '/src/styles/globals.css';
const root=createRoot(document.getElementById('probe'));
window.mountWord = async (text) => {
 const zip=new JSZip();
 zip.file('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>');
 zip.file('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>');
 zip.file('word/_rels/document.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>');
 zip.file('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'+text+'</w:t></w:r></w:p><w:p><w:r><w:br w:type="page"/><w:t>Trang thứ hai</w:t></w:r></w:p><w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr></w:body></w:document>');
 const blob=await zip.generateAsync({type:'blob'});
 root.render(React.createElement(DocxViewer,{blob,blobUrl:URL.createObjectURL(blob),fileName:'sample.docx'}));
};
window.mountBadWord = () => root.render(React.createElement(DocxViewer,{blob:new Blob(['invalid'])}));
window.mountPublication = (props) => {
 const client = new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});
 function Host(){const [open,setOpen]=React.useState(true);return React.createElement(React.Fragment,null,
 React.createElement('button',{onClick:()=>setOpen(true)},'Mở lại'),
 React.createElement(PublicationDialog,{...props,open,onOpenChange:setOpen}));}
 root.render(React.createElement(QueryClientProvider,{client},React.createElement(Host)));
};
window.mountDelete = async () => {
 const {LifecycleDeleteDialog}=await import('/src/components/knowledge/lifecycle-delete-dialog.tsx');
 const client=new QueryClient({defaultOptions:{mutations:{retry:false}}});
 function Host(){const [open,setOpen]=React.useState(true);return React.createElement(LifecycleDeleteDialog,{open,onOpenChange:setOpen,workspaceId:'ws_test',sourceId:'src_test',sourceTitle:'Tài liệu kiểm tra'});}
 root.render(React.createElement(QueryClientProvider,{client},React.createElement(Host)));
};
window.mountStudio = async (location = '/knowledge/src_test?collectionId=col_test') => {
 const {createRouter,createMemoryHistory,RouterProvider}=await import('@tanstack/react-router');
 const {routeTree}=await import('/src/routeTree.gen.ts');
 const {useUiStore}=await import('/src/lib/ui-store.ts');
 useUiStore.getState().setActiveWorkspace({id:'ws_test',code:'shl',name:'Đơn vị kiểm tra'});
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 const router=createRouter({routeTree,history:createMemoryHistory({initialEntries:[location]})});
 root.render(React.createElement(QueryClientProvider,{client},React.createElement(RouterProvider,{router})));
};
window.mountTasks = async (tasks) => {
 const {createRouter,createRootRoute,createMemoryHistory,RouterProvider}=await import('@tanstack/react-router');
 const {BackgroundTasksBar}=await import('/src/components/knowledge/background-tasks-bar.tsx');
 const {AppNotifications}=await import('/src/components/ui/app-notifications.tsx');
 const {useBackgroundTasksStore}=await import('/src/lib/background-tasks-store.ts');
 const {useUiStore}=await import('/src/lib/ui-store.ts');
 const {toast}=await import('sonner');
 useUiStore.getState().setActiveWorkspaceId('ws_test');
 useBackgroundTasksStore.setState({tasks,isExpanded:true});
 window.taskStore=useBackgroundTasksStore;
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 window.refreshTaskReads=()=>client.invalidateQueries({queryKey:['v1','preparation']});
 window.showTaskToast=()=>toast.success('Đã nhận tài liệu kiểm tra.');
 window.switchTaskWorkspace=(id)=>useUiStore.getState().setActiveWorkspaceId(id);
 window.setTaskTheme=(theme)=>useUiStore.getState().setTheme(theme);
 const rootRoute=createRootRoute({component:()=>React.createElement(React.Fragment,null,
   React.createElement(BackgroundTasksBar),React.createElement(AppNotifications))});
 const router=createRouter({routeTree:rootRoute,history:createMemoryHistory({initialEntries:['/']})});
 root.render(React.createElement(QueryClientProvider,{client},React.createElement(RouterProvider,{router})));
};
window.testReady=true;
</script></body></html>`;
before(async () => {
  server = await createServer({
    appType: "custom",
    logLevel: "error",
    server: { host: "127.0.0.1", port: 0, open: false },
  });
  server.middlewares.use("/__studio_regression__", async (_req, res) => {
    res.setHeader("Content-Type", "text/html");
    res.end(await server.transformIndexHtml("/__studio_regression__", html));
  });
  await server.listen();
  url = `http://127.0.0.1:${server.httpServer.address().port}/__studio_regression__`;
  browser = await chromium.launch({ headless: true });
});
after(async () => {
  await browser?.close();
  await server?.close();
});
async function pageForTest() {
  const page = await browser.newPage({
    viewport: { width: 1000, height: 800 },
  });
  const errors = [];
  page.setDefaultTimeout(10000);
  page.on("pageerror", (err) => {
    errors.push(err.message);
    console.error(err.message);
  });
  await page.goto(url);
  await page.waitForFunction(() => window.testReady, null, { timeout: 10000 });
  return { page, errors };
}
const sha = "a".repeat(64),
  metaSha = "b".repeat(64);

test("source deletion confirms once using the preview ID returned by the API", async () => {
  const { page, errors } = await pageForTest();
  const requests = [];
  const preview = {
    id: "lca_test",
    kind: "source",
    resource_id: "src_test",
    action: "delete",
    status: "preview",
    preview_sha256: sha,
    impact: { permanent: true },
    expires_at: "2026-11-11T00:00:00Z",
  };
  try {
    await page.route("**/workspaces/ws_test/lifecycle/*", async (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      requests.push({
        path: path.split("/").at(-1),
        key: request.headers()["idempotency-key"],
        body: request.postDataJSON(),
      });
      await route.fulfill({
        json: path.endsWith("/previews")
          ? preview
          : { ...preview, status: "pending" },
      });
    });
    await page.evaluate(() => window.mountDelete());
    await page
      .getByRole("button", { name: "Xóa tài liệu", exact: true })
      .click();
    await page.getByRole("dialog").waitFor({ state: "hidden" });
    assert.deepEqual(
      requests.map(({ path }) => path),
      ["previews", "actions"],
    );
    assert.equal(requests[1].key, "lifecycle:lca_test");
    assert.deepEqual(requests[1].body, {
      preview_id: "lca_test",
      preview_sha256: sha,
    });
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
});

test("settings does not show model configuration or a session when access cannot be verified", async () => {
  for (const authStatus of [200, 503]) {
    const { page, errors } = await pageForTest();
    const modelRequests = [];
    try {
      await page.route("**/platform/v1alpha1/**", async (route) => {
        const path = new URL(route.request().url()).pathname;
        if (path.includes("/modelops/")) modelRequests.push(path);
        if (path.endsWith("/auth/me")) {
          return route.fulfill({
            status: authStatus,
            json: {
              actor: { authenticated: true, permissions: [], roles: [] },
            },
          });
        }
        return route.fulfill({ json: { items: [] } });
      });
      await page.evaluate(() => window.mountStudio("/settings"));
      await page
        .getByRole("button", { name: "Mô hình mặc định", exact: true })
        .click();
      await page
        .getByText(
          authStatus === 200
            ? "Bạn không có quyền xem cấu hình mô hình hệ thống."
            : "Không thể tải thông tin tài khoản.",
          { exact: true },
        )
        .waitFor();
      assert.equal(await page.getByRole("combobox").count(), 0);
      assert.equal(
        await page.getByText("Đã đồng bộ với cấu hình hệ thống").count(),
        0,
      );
      assert.deepEqual(modelRequests, []);
      if (authStatus === 503) {
        await page
          .getByRole("button", { name: "Tài khoản", exact: true })
          .click();
        await page
          .getByRole("alert")
          .filter({ hasText: "Không thể tải thông tin tài khoản." })
          .waitFor();
        const settings = page.getByRole("main");
        assert.equal(
          await settings.getByText("Đã đăng nhập", { exact: true }).count(),
          0,
        );
        assert.equal(
          await settings.getByText("dev@qnu.edu.vn", { exact: true }).count(),
          0,
        );
      }
      assert.deepEqual(errors, []);
    } finally {
      await page.close();
    }
  }
});

test("settings only reports synchronization after all model data loads", async () => {
  const { page, errors } = await pageForTest();
  let connectionStatus = 503;
  try {
    await page.route("**/platform/v1alpha1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/auth/me")) {
        return route.fulfill({
          json: {
            actor: {
              authenticated: true,
              permissions: ["ai.models.manage"],
              roles: [],
            },
          },
        });
      }
      if (path.endsWith("/modelops/defaults"))
        return route.fulfill({ json: {} });
      if (path.endsWith("/modelops/providers"))
        return route.fulfill({ json: [] });
      if (path.endsWith("/modelops/connections")) {
        return route.fulfill({ status: connectionStatus, json: [] });
      }
      return route.fulfill({ json: { items: [] } });
    });
    await page.evaluate(() => window.mountStudio("/settings"));
    await page
      .getByRole("button", { name: "Mô hình mặc định", exact: true })
      .click();
    const error = page
      .getByRole("alert")
      .filter({ hasText: "Không thể tải cấu hình" });
    await error.waitFor();
    assert.equal(await page.getByRole("combobox").count(), 0);
    assert.equal(
      await page.getByText("Đã đồng bộ với cấu hình hệ thống").count(),
      0,
    );
    connectionStatus = 200;
    await page.getByRole("button", { name: "Thử lại", exact: true }).click();
    await page.getByText("Đã đồng bộ với cấu hình hệ thống").waitFor();
    assert.equal(await page.getByRole("combobox").count(), 4);
    assert.equal(await error.count(), 0);
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
});
const props = {
  canRegister: true,
  workspaceId: "ws_test",
  collectionId: "col_test",
  sourceTitle: "Tài liệu kiểm tra",
  compilationRunId: "cmp_test",
};
function version(status = "approved", run = "cmp_test") {
  return {
    id: "ver_test",
    document_id: "doc_test",
    compilation_run_id: run,
    status,
    bundle_sha256: sha,
    retrieval_metadata_sha256: metaSha,
    version_no: 1,
    state_version: 2,
  };
}
function ref(status = "approved") {
  return {
    version_id: "ver_test",
    document_id: "doc_test",
    status,
    bundle_sha256: sha,
  };
}
async function mockApi(
  page,
  {
    status = "approved",
    run = "cmp_test",
    loseCommit = false,
    loseRegister = false,
    expireCommit = false,
    gate = null,
    canPublish = true,
    served = true,
  } = {},
) {
  const calls = [];
  const previewActions = new Map();
  let previews = 0,
    commits = 0,
    registrations = 0;
  await page.route("**/platform/v1alpha1/**", async (route) => {
    const request = route.request(),
      path = new URL(request.url()).pathname,
      method = request.method();
    const body = method === "POST" ? request.postDataJSON() : null;
    calls.push({
      method,
      path,
      body,
      key: request.headers()["idempotency-key"],
    });
    const send = (data, code = 200) =>
      route.fulfill({
        status: code,
        contentType: "application/json",
        body: JSON.stringify(data),
      });
    if (path.endsWith("/review-gate"))
      return gate
        ? send(gate)
        : send(
            { code: "publication_review_required", detail: "Chưa có review" },
            409,
          );
    if (path.endsWith("/summary"))
      return send({
        document: { id: "doc_test" },
        prepared_version: version(status, run),
        published_version: status === "published" ? version(status, run) : null,
        served_version:
          status === "published" && served ? version(status, run) : null,
        readiness: {
          status: status === "published" && served ? "ready" : "not_indexed",
        },
        serving_matches_published: status === "published" && served,
        capabilities: {
          can_register: true,
          can_prepare: true,
          can_approve: true,
          can_publish: canPublish,
        },
        versions: { items: [], meta: { page: 1, page_size: 20, total: 0 } },
      });
    if (method === "GET" && path.endsWith("/versions/ver_test"))
      return send(version(status, run));
    if (path.endsWith("/decision-preview")) {
      const id = `preview_${++previews}`;
      previewActions.set(id, body.action);
      return send({
        id,
        preview_sha256: sha,
        action: body.action,
        version_id: "ver_test",
      });
    }
    if (path.endsWith("/decisions")) {
      commits++;
      if (loseCommit && commits === 1) return route.abort("failed");
      if (expireCommit && commits === 1)
        return send(
          {
            code: "publication_preview_expired",
            detail: "Preview hết hạn; cần xác nhận lại.",
          },
          409,
        );
      status =
        previewActions.get(body.preview_id) === "approve"
          ? "approved"
          : "published";
      return send({ id: "decision_test" });
    }
    if (
      method === "POST" &&
      (path.endsWith("/compiled-documents") || path.endsWith("/versions"))
    ) {
      registrations++;
      if (loseRegister && registrations === 1) return route.abort("failed");
      return send(
        {
          document: { id: "doc_test" },
          version: version("draft"),
          created: true,
        },
        201,
      );
    }
    return send({ detail: "Unexpected mock API call" }, 500);
  });
  return calls;
}
test("Word mounts immediately, fits width, zooms and replaces the document", async () => {
  const { page, errors } = await pageForTest();
  try {
    await page.evaluate(() => window.mountWord("Văn bản đầu tiên"));
    await page.locator("section.docx-preview-content").first().waitFor();
    await page.waitForFunction(
      () =>
        !document.body.textContent.includes(
          "Đang chuẩn bị xem trước tài liệu Word",
        ),
    );
    assert.equal(await page.locator("section.docx-preview-content").count(), 2);
    const natural = await page
      .locator("section.docx-preview-content")
      .first()
      .evaluate((el) => el.offsetWidth);
    await page.setViewportSize({ width: 390, height: 800 });
    await page.waitForFunction(
      () =>
        document
          .querySelector("section.docx-preview-content")
          .getBoundingClientRect().width < 390,
    );
    assert.equal(
      await page
        .locator("section.docx-preview-content")
        .first()
        .evaluate((el) => el.offsetWidth),
      natural,
      "fit must scale, not reflow Word",
    );
    const fitted = await page
      .locator("section.docx-preview-content")
      .first()
      .evaluate((el) => el.getBoundingClientRect().width);
    await page.getByRole("button", { name: "Phóng to", exact: true }).click();
    assert.ok(
      (await page
        .locator("section.docx-preview-content")
        .first()
        .evaluate((el) => el.getBoundingClientRect().width)) > fitted,
    );
    await page.evaluate(() => window.mountWord("Văn bản mới"));
    await page.getByText("Văn bản mới", { exact: true }).waitFor();
    assert.equal(
      await page.getByText("Văn bản đầu tiên", { exact: true }).count(),
      0,
    );
    assert.deepEqual(errors, []);
  } catch (err) {
    console.error(await page.locator("body").textContent());
    throw err;
  } finally {
    await page.close();
  }
});
test("Word render failure is visible and a subsequent valid blob recovers", async () => {
  const { page, errors } = await pageForTest();
  try {
    await page.evaluate(() => window.mountBadWord());
    await page.getByText("Không thể hiển thị xem trước trực tiếp:").waitFor();
    await page.evaluate(() => window.mountWord("Khôi phục xem Word"));
    await page.getByText("Khôi phục xem Word", { exact: true }).waitFor();
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
});
test("approved version resumes publication; a lost response replays the same receipt once on user request", async () => {
  const { page, errors } = await pageForTest();
  try {
    const calls = await mockApi(page, { loseCommit: true });
    await page.evaluate((p) => window.mountPublication(p), {
      ...props,
      existingDocumentId: "doc_test",
      existingVersion: ref(),
    });
    await page.getByRole("button", { name: "Phát hành", exact: true }).click();
    await page.getByRole("button", { name: "Thử lại cùng thao tác" }).waitFor();
    assert.equal(calls.filter((c) => c.path.endsWith("/decisions")).length, 1);
    await page.getByRole("button", { name: "Thử lại cùng thao tác" }).click();
    await page
      .getByText("Sẵn sàng phục vụ hỏi đáp.", { exact: true })
      .waitFor();
    assert.equal(
      calls.filter((c) => c.path.endsWith("/decision-preview")).length,
      1,
    );
    const commits = calls.filter((c) => c.path.endsWith("/decisions"));
    assert.deepEqual(commits[0], commits[1]);
    assert.ok(commits[0].key);
    assert.equal(
      calls.filter(
        (c) =>
          c.method === "POST" &&
          (c.path.endsWith("/compiled-documents") ||
            c.path.endsWith("/versions")),
      ).length,
      0,
    );
    await page
      .getByRole("button", { name: "Đóng", exact: true })
      .first()
      .click();
    await page.getByRole("button", { name: "Mở lại", exact: true }).click();
    await page
      .getByText("Sẵn sàng phục vụ hỏi đáp.", { exact: true })
      .waitFor();
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
});
test("registration retry is stable and review bypass requires explicit confirmation and reason", async () => {
  const { page, errors } = await pageForTest();
  try {
    const calls = await mockApi(page, { status: "draft", loseRegister: true });
    await page.evaluate((p) => window.mountPublication(p), props);
    await page.getByRole("button", { name: "Tiếp tục", exact: true }).click();
    await page.getByRole("alert").waitFor();
    await page.getByRole("button", { name: "Tiếp tục", exact: true }).click();
    await page
      .getByText("Chưa có báo cáo rà soát hoàn tất cho phiên bản này.")
      .waitFor();
    const regs = calls.filter((c) => c.path.endsWith("/compiled-documents"));
    assert.equal(regs.length, 2);
    assert.deepEqual(regs[0], regs[1]);
    const approve = page.getByRole("button", {
      name: "Xác nhận duyệt",
      exact: true,
    });
    assert.equal(await approve.isDisabled(), true);
    await page
      .getByRole("checkbox", { name: "Duyệt không dùng báo cáo AI" })
      .check();
    await page
      .getByRole("textbox", { name: "Lý do duyệt không dùng báo cáo AI" })
      .fill("Đã kiểm tra trực tiếp với bản gốc.");
    assert.equal(await approve.isDisabled(), true);
    await page
      .getByRole("checkbox", { name: "Tôi đã đối chiếu", exact: false })
      .check();
    await approve.click();
    await page
      .getByRole("button", { name: "Phát hành", exact: true })
      .waitFor();
    const request = calls.find((c) => c.path.endsWith("/decision-preview"));
    assert.equal(request.body.review_skip.bundle_sha256, sha);
    assert.equal(request.body.review_skip.retrieval_metadata_sha256, metaSha);
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
});
test("new edited run registers a version on the existing document", async () => {
  const { page } = await pageForTest();
  try {
    const calls = await mockApi(page, { status: "draft" });
    await page.evaluate((p) => window.mountPublication(p), {
      ...props,
      existingDocumentId: "doc_test",
    });
    await page.getByRole("button", { name: "Tiếp tục", exact: true }).click();
    await page
      .getByText("Chưa có báo cáo rà soát hoàn tất cho phiên bản này.")
      .waitFor();
    assert.equal(
      calls.filter(
        (c) => c.method === "POST" && c.path.endsWith("/compiled-documents"),
      ).length,
      0,
    );
    assert.equal(
      calls.filter(
        (c) => c.method === "POST" && c.path.endsWith("/doc_test/versions"),
      ).length,
      1,
    );
  } finally {
    await page.close();
  }
});
test("review findings require a decision and explanation; publication respects role", async () => {
  const { page } = await pageForTest();
  try {
    const calls = await mockApi(page, {
      status: "draft",
      canPublish: false,
      gate: {
        review_id: "review_test",
        report_sha256: sha,
        bundle_sha256: sha,
        findings: [
          {
            finding_id: "f_test",
            finding: { explanation: "Đối chiếu số liệu với nguồn." },
          },
        ],
      },
    });
    await page.evaluate((p) => window.mountPublication(p), {
      ...props,
      existingVersion: ref("draft"),
    });
    await page
      .getByText("Đối chiếu số liệu với nguồn.", { exact: false })
      .waitFor();
    await page
      .getByRole("checkbox", { name: "Tôi đã đối chiếu", exact: false })
      .check();
    const approve = page.getByRole("button", {
      name: "Xác nhận duyệt",
      exact: true,
    });
    assert.equal(await approve.isDisabled(), true);
    await page
      .getByRole("textbox", { name: "Giải trình nhận xét 1" })
      .fill("Đã đối chiếu, số liệu đúng với nguồn.");
    assert.equal(await approve.isDisabled(), true);
    await page
      .getByRole("combobox", { name: "Xử lý nhận xét 1" })
      .selectOption("not_an_issue");
    await approve.click();
    const publish = page.getByRole("button", {
      name: "Phát hành",
      exact: true,
    });
    await publish.waitFor();
    assert.equal(await publish.isDisabled(), true);
    const request = calls.find((c) => c.path.endsWith("/decision-preview"));
    assert.equal(request.body.review_skip, undefined);
    assert.equal(
      request.body.review_ack.resolutions[0].decision,
      "not_an_issue",
    );
  } finally {
    await page.close();
  }
});
test("a version belonging to another compilation cannot be approved or published", async () => {
  const { page } = await pageForTest();
  try {
    const calls = await mockApi(page, { run: "cmp_other" });
    await page.evaluate((p) => window.mountPublication(p), {
      ...props,
      existingVersion: ref(),
    });
    await page
      .getByText("Chưa xác nhận được phiên bản khớp bản đang xem.")
      .waitFor();
    assert.equal(
      await page
        .getByRole("button", { name: "Phát hành", exact: true })
        .count(),
      0,
    );
    assert.equal(calls.filter((c) => c.method === "POST").length, 0);
  } finally {
    await page.close();
  }
});

test("Studio desktop/mobile layout has one Word toolbar, one served badge and canonical citations", async () => {
  const { page, errors } = await pageForTest();
  try {
    const JSZip = require("jszip");
    const zip = new JSZip();
    zip.file(
      "[Content_Types].xml",
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/></Types>',
    );
    zip.file(
      "_rels/.rels",
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
    );
    zip.file(
      "word/_rels/document.xml.rels",
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
    );
    zip.file(
      "word/document.xml",
      '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Tài liệu thử nghiệm trình bày</w:t></w:r></w:p><w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr></w:body></w:document>',
    );
    const docx = await zip.generateAsync({ type: "nodebuffer" });
    const source = {
      id: "src_test",
      title: "Tai_lieu_kiem_tra",
      file_name: "Tai_lieu_kiem_tra.docx",
      content_type:
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      current_revision_no: 1,
      serving_revision_no: 1,
      status: "ready",
    };
    const revision = {
      id: "rev_test",
      revision_no: 1,
      file_name: source.file_name,
    };
    const draft = {
      title: source.title,
      sections: [
        {
          heading: "Nguồn 1 · Phần 1",
          paragraphs: [
            {
              text: "Thông tin nhận diện của trường.",
              citations: ["ev_p001_b001"],
            },
          ],
        },
      ],
      source_tables: [],
      citations: {
        ev_p001_b001: {
          page: 1,
          source_id: "src_test",
          revision_id: "rev_test",
          source_locator: { format: "docx" },
        },
      },
      sources: [],
      unknowns: [],
    };
    const caps = {
      can_prepare: true,
      can_register: true,
      can_approve: true,
      can_publish: true,
    };
    const markdownBytes = Buffer.from(
      "# Nội dung kiểm tra\r\n\r\n> Bản nháp chưa duyệt.\r\n\r\nĐoạn thử [ev_p001_b001]\r\n",
    );
    const jsonBytes = Buffer.from('{ "title": "Nội dung kiểm tra" }\n');
    await page.route("**/platform/v1alpha1/**", async (route) => {
      assert.equal(
        route.request().method(),
        "GET",
        "layout verification is read-only",
      );
      const path = new URL(route.request().url()).pathname;
      const send = (data) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(data),
        });
      if (path.endsWith("/content"))
        return route.fulfill({
          status: 200,
          contentType: source.content_type,
          body: docx,
        });
      if (path.endsWith("/sources/src_test/summary"))
        return send({
          revision,
          derivations: [
            {
              compilation_run_id: "cmp_test",
              compilation_generation: 1,
              compilation_status: "completed",
              is_serving: true,
              readiness: { status: "ready" },
              version: { ...ref("published"), version_no: 1 },
            },
          ],
          serving: {
            served_document_id: "doc_test",
            served_version_id: "ver_test",
            served_revision_no: 1,
          },
          processing_runs: [],
          actions: {},
          capabilities: caps,
        });
      if (path.endsWith("/sources/src_test")) return send(source);
      if (path.endsWith("/revisions")) return send([revision]);
      if (path.endsWith("/draft")) return send(draft);
      if (path.endsWith("/draft.json"))
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: jsonBytes,
        });
      if (path.endsWith("/markdown"))
        return route.fulfill({
          status: 200,
          contentType: "text/markdown",
          body: markdownBytes,
        });
      if (path.endsWith("/edit-context"))
        return send({ content: draft, bundle_sha256: sha });
      return send({ items: [], meta: { page: 1, page_size: 20, total: 0 } });
    });
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.evaluate(() => window.mountStudio());
    await page.locator("section.docx-preview-content").waitFor();
    assert.equal(
      await page.getByText("Tệp gốc · DOCX", { exact: true }).count(),
      1,
    );
    assert.equal(
      await page.getByText("Sẵn sàng phục vụ", { exact: true }).count(),
      1,
    );
    await page
      .getByRole("button", { name: "Xem nguồn trích dẫn số [1]", exact: true })
      .click();
    await page
      .getByText("Vị trí trong tài liệu Word", { exact: true })
      .waitFor();
    assert.equal(
      await page.getByText("Trang 1, khối 1", { exact: true }).count(),
      0,
    );
    await page.keyboard.press("Escape");
    await page
      .getByText("Căn cứ trích dẫn [1]", { exact: true })
      .waitFor({ state: "hidden" });
    await mkdir("../tmp/studio-919", { recursive: true });
    await page.screenshot({ path: "../tmp/studio-919/desktop.png" });
    await page.getByRole("tab", { name: "Markdown" }).click();
    await page.getByText("Đoạn thử", { exact: true }).waitFor();
    assert.equal(
      await page.getByText("Bản nháp chưa duyệt.", { exact: true }).count(),
      0,
    );
    assert.equal(
      await page.locator("article").getByText("[1]", { exact: true }).count(),
      1,
    );
    const mdDownload = page.waitForEvent("download");
    await page.getByRole("button", { name: "Tải .md" }).click();
    assert.deepEqual(
      await readFile(await (await mdDownload).path()),
      markdownBytes,
    );
    await page.getByRole("button", { name: "Thao tác phụ" }).click();
    const jsonDownload = page.waitForEvent("download");
    await page.getByRole("menuitem", { name: "Tải tệp JSON" }).click();
    assert.deepEqual(
      await readFile(await (await jsonDownload).path()),
      jsonBytes,
    );
    await page.getByRole("tab", { name: "Nội dung", exact: true }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page
      .getByRole("button", { name: "Nội dung đã chuẩn bị", exact: true })
      .waitFor();
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
      "mobile page must not scroll horizontally",
    );
    assert.ok(
      (await page
        .locator("article")
        .filter({ hasText: "Thông tin nhận diện của trường." })
        .evaluate((el) => el.clientWidth)) >= 300,
      "mobile reading area must remain usable",
    );
    await page.screenshot({ path: "../tmp/studio-919/mobile.png" });
    await page
      .getByRole("button", { name: "Mở menu điều hướng", exact: true })
      .click();
    await page
      .getByRole("dialog", { name: "Điều hướng", exact: true })
      .waitFor();
    await page
      .getByRole("dialog", { name: "Điều hướng", exact: true })
      .getByRole("link", { name: "Kho tri thức", exact: true })
      .click();
    await page
      .getByRole("dialog", { name: "Điều hướng", exact: true })
      .waitFor({ state: "hidden" });
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
});

test("spelling review keeps the PDF URL and prepares the saved version with exact edits", async () => {
  const { page, errors } = await pageForTest();
  const preparation = [];
  let saves = 0;
  let checksAvailable = false;
  const unit = {
    evidence_id: "ev_1",
    page: 2,
    kind: "paragraph",
    text: "Xin chào bạ",
    original_text: "Xin chào bạ",
    bbox: {},
  };
  const review = {
    run_id: "ocr_test",
    version: 0,
    version_id: null,
    canonical_sha256: sha,
    original_sha256: sha,
    units: [unit],
  };
  const revision = { id: "rev_test", revision_no: 1, file_name: "test.pdf" };
  const source = {
    id: "src_test",
    title: "Tài liệu kiểm tra",
    file_name: "test.pdf",
  };
  try {
    await page.route("**/platform/v1alpha1/**", async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      const path = url.pathname;
      const send = (data, status = 200) =>
        route.fulfill({ status, json: data });
      if (path.endsWith("/sources/src_test/summary"))
        return send({
          revision,
          active_run_id: "ocr_test",
          processing_runs: [
            { id: "ocr_test", status: "completed", revision_id: "rev_test" },
          ],
          derivations: [{ ocr_run_id: "ocr_test", version: { version_no: 7 } }],
        });
      if (path.endsWith("/sources/src_test")) return send(source);
      if (path.endsWith("/content"))
        return route.fulfill({
          contentType: "application/pdf",
          body: "%PDF-1.4\nfixture",
        });
      if (path.endsWith("/text-review/checks")) {
        assert.equal(url.searchParams.has("version"), false);
        if (!checksAvailable)
          return send({ detail: "Method Not Allowed" }, 405);
        return send([
          {
            ...review,
            id: "spl_test",
            status: "completed",
            total_evidence_count: 1,
            checked_evidence_ids: ["ev_1"],
            suggestions: [
              {
                evidence_id: "ev_1",
                start: 9,
                end: 11,
                original: "bạ",
                replacement: "bạn",
                reason: "Thiếu chữ.",
              },
            ],
          },
        ]);
      }
      if (path.endsWith("/text-review") && request.method() === "GET") {
        assert.equal(url.searchParams.has("version"), false);
        return send(review);
      }
      if (path.endsWith("/text-review")) {
        saves++;
        assert.equal(request.postDataJSON().changes[0].after, "Xin chào bạn");
        assert.deepEqual(request.postDataJSON().changes[0].spelling_edits, [
          { start: 9, end: 11, replacement: "bạn" },
        ]);
        return send({ ...review, version: 1, version_id: "txt_saved" });
      }
      if (
        path.endsWith("/preparation-intents") &&
        request.method() === "POST"
      ) {
        preparation.push({
          key: request.headers()["idempotency-key"],
          body: request.postDataJSON(),
        });
        return send({ intent: { id: "prep_saved" } }, 201);
      }
      return send({ items: [], meta: { page: 1, page_size: 20, total: 0 } });
    });
    await page.evaluate(() =>
      window.mountStudio("/knowledge/src_test/review?collectionId=col_test"),
    );
    const alert = page.getByRole("alert").filter({
      hasText: "Không tải được kết quả soát chính tả",
    });
    await alert.waitFor();
    assert.match(await alert.textContent(), /chưa hỗ trợ đọc danh sách gợi ý/);
    assert.equal(await page.getByText("Chưa có gợi ý để hiển thị").count(), 0);
    checksAvailable = true;
    await page.getByRole("button", { name: "Thử tải lại" }).click();
    await page.getByRole("button", { name: "Đối chiếu tệp gốc" }).click();
    const pdf = page.locator('iframe[title="Bản gốc PDF"]');
    await pdf.waitFor();
    assert.equal(
      await pdf.evaluate(
        async (frame) => (await fetch(frame.src.split("#")[0])).ok,
      ),
      true,
    );
    await page.getByRole("button", { name: "Áp dụng", exact: true }).click();
    await page.getByTitle("Hoàn tất duyệt chính tả (S)").click();
    await page
      .getByRole("dialog", { name: "Hoàn tất duyệt chính tả" })
      .getByRole("button", { name: "Hoàn tất duyệt", exact: true })
      .click();
    await page.waitForFunction(
      () => !document.querySelector('iframe[title="Bản gốc PDF"]'),
    );
    assert.equal(saves, 1);
    assert.equal(preparation.length, 1);
    assert.ok(preparation[0].key);
    assert.equal(preparation[0].body.text_version, 1);
    assert.equal(preparation[0].body.revision_id, "rev_test");
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
});

test("expired approval preview requires fresh confirmation and a new receipt", async () => {
  const { page } = await pageForTest();
  try {
    const calls = await mockApi(page, { status: "draft", expireCommit: true });
    await page.evaluate((p) => window.mountPublication(p), {
      ...props,
      existingVersion: ref("draft"),
    });
    await page
      .getByRole("checkbox", { name: "Duyệt không dùng báo cáo AI" })
      .check();
    await page
      .getByRole("textbox", { name: "Lý do duyệt không dùng báo cáo AI" })
      .fill("Đã kiểm tra trực tiếp với bản gốc.");
    const confirmation = page.getByRole("checkbox", {
      name: "Tôi đã đối chiếu",
      exact: false,
    });
    await confirmation.check();
    await page
      .getByRole("button", { name: "Xác nhận duyệt", exact: true })
      .click();
    await page
      .getByRole("alert")
      .filter({ hasText: "Preview hết hạn" })
      .waitFor();
    assert.equal(await confirmation.isChecked(), false);
    assert.equal(calls.filter((c) => c.path.endsWith("/decisions")).length, 1);
    await confirmation.check();
    await page
      .getByRole("button", { name: "Xác nhận duyệt", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Phát hành", exact: true })
      .waitFor();
    const commits = calls.filter((c) => c.path.endsWith("/decisions"));
    assert.equal(commits.length, 2);
    assert.notEqual(commits[0].key, commits[1].key);
    assert.notEqual(commits[0].body.preview_id, commits[1].body.preview_id);
  } finally {
    await page.close();
  }
});

const backgroundTask = {
  id: "prep_test",
  kind: "preparation",
  workspaceId: "ws_test",
  collectionId: "col_test",
  sourceId: "src_test",
  sourceTitle: "Thông tin tuyển sinh có tên dài để kiểm tra hiển thị",
  fileName: "sample.pdf",
  status: "queued",
  step: "Đã nhận yêu cầu",
  errorCode: null,
  createdAt: "2026-11-10T00:00:00Z",
};
async function mockTaskApi(page, state) {
  const calls = [];
  await page.route("**/platform/v1alpha1/**", async (route) => {
    const request = route.request(),
      path = new URL(request.url()).pathname;
    calls.push({ method: request.method(), path });
    const json = (data, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(data),
      });
    if (path.endsWith("/prep_test/cancel")) {
      state.status = "cancelled";
      return json({ ...state.intent, status: state.status });
    }
    if (path.endsWith("/preparation-intents/prep_test")) {
      if (state.offline)
        return json(
          { code: "service_unavailable", detail: "Không kết nối" },
          503,
        );
      return json({
        id: "prep_test",
        workspace_id: "ws_test",
        collection_id: "col_test",
        source_id: "src_test",
        revision_id: "rev_pinned",
        revision_no: 1,
        ocr_run_id: "ocr_pinned",
        compilation_run_id: "cmp_pinned",
        status: state.status,
        step:
          state.status === "waiting_ocr"
            ? "Đang đọc nội dung"
            : state.status === "ready"
              ? "Đã chuẩn bị xong"
              : "Đang chuẩn bị nội dung",
        error_code: null,
      });
    }
    if (path.endsWith("/processing-runs/ocr_pinned"))
      return json({
        id: "ocr_pinned",
        status: "running",
        pages_done: state.done,
        pages_total: state.total,
        pagination: state.pagination ?? "page",
      });
    if (path.endsWith("/compilation-runs/cmp_pinned/progress"))
      return json({
        run_id: "cmp_pinned",
        status: "running",
        completed: state.done,
        total: state.total,
      });
    return json({ detail: "Unexpected request" }, 404);
  });
  return calls;
}
test("background: measured stage progress and notifications do not overlap on desktop/mobile", async () => {
  const { page, errors } = await pageForTest();
  try {
    const state = { status: "waiting_ocr", done: 4, total: 8 };
    const calls = await mockTaskApi(page, state);
    await page.evaluate((task) => window.mountTasks([task]), backgroundTask);
    await page.getByText("Đã đọc 4/8 trang").waitFor();
    assert.equal(
      await page.getByRole("progressbar").getAttribute("aria-valuenow"),
      "25",
    );
    for (const [name, width, height, dark] of [
      ["desktop", 1440, 900, false],
      ["mobile", 390, 844, false],
      ["mobile-dark", 390, 844, true],
    ]) {
      await page.setViewportSize({ width, height });
      await page.evaluate(
        (d) => window.setTaskTheme(d ? "dark" : "light"),
        dark,
      );
      await page.evaluate(() => window.showTaskToast());
      const toast = page.locator("[data-sonner-toast]").first();
      await toast.waitFor();
      await page.waitForFunction(() =>
        Array.from(document.querySelectorAll("[data-sonner-toast]")).every(
          (el) => el.getAttribute("data-mounted") === "true",
        ),
      );
      await toast.evaluate((el) =>
        el.getAnimations().forEach((animation) => {
          animation.finish();
        }),
      );
      const panel = await page
        .getByRole("region", { name: "Tác vụ xử lý tài liệu" })
        .boundingBox();
      const notice = await toast.boundingBox();
      assert.ok(panel && notice);
      assert.ok(
        notice.y + notice.height < panel.y || panel.y + panel.height < notice.y,
        "toast must not cover task panel",
      );
      assert.ok(panel.x >= 0 && panel.x + panel.width <= width);
      await mkdir("../tmp/background-920", { recursive: true });
      await page.screenshot({ path: `../tmp/background-920/${name}.png` });
    }
    assert.ok(
      calls.some((c) =>
        c.path.includes("/revisions/rev_pinned/processing-runs/ocr_pinned"),
      ),
    );
    assert.equal(calls.filter((c) => c.method !== "GET").length, 0);
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
});
test("background: unknown totals stay indeterminate and combined progress never resets", async () => {
  const { page, errors } = await pageForTest();
  try {
    const state = {
      status: "waiting_ocr",
      done: 0,
      total: null,
      pagination: "document",
    };
    await mockTaskApi(page, state);
    await page.evaluate((task) => window.mountTasks([task]), backgroundTask);
    await page.getByText("Đang phân tích tệp…").waitFor();
    assert.equal(
      await page.getByRole("progressbar").getAttribute("aria-valuenow"),
      null,
    );
    state.total = 1;
    state.done = 1;
    await page.evaluate(() => window.refreshTaskReads());
    await page.getByText("Đã đọc 1/1 đơn vị").waitFor();
    assert.equal(
      await page.getByRole("progressbar").getAttribute("aria-valuenow"),
      "50",
    );
    state.status = "compiling";
    state.done = 1;
    state.total = 4;
    await page.evaluate(() => window.refreshTaskReads());
    await page.getByText("Đã chuẩn bị 1/4 phần").waitFor();
    assert.equal(
      await page.getByRole("progressbar").getAttribute("aria-valuenow"),
      "61",
    );
    state.status = "ready";
    await page.evaluate(() => window.refreshTaskReads());
    await page.getByRole("link", { name: "Mở bản nháp" }).waitFor();
    assert.equal(
      await page.getByRole("progressbar").getAttribute("aria-valuenow"),
      "100",
    );
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
});
test("background: polling recovers from connection loss even when collapsed; no false uncertain", async () => {
  const { page, errors } = await pageForTest();
  try {
    const state = { status: "compiling", done: 1, total: 4, offline: true };
    const calls = await mockTaskApi(page, state);
    await page.evaluate((task) => window.mountTasks([task]), backgroundTask);
    await page.getByText("Mất kết nối theo dõi.", { exact: false }).waitFor();
    assert.equal(
      await page.evaluate(() => window.taskStore.getState().tasks[0].status),
      "queued",
    );
    await page.getByRole("button", { name: "Thu gọn bảng tác vụ" }).click();
    state.offline = false;
    state.status = "ready";
    await page.waitForFunction(
      () => window.taskStore.getState().tasks[0].status === "ready",
    );
    await page.getByRole("button", { name: "Mở rộng bảng tác vụ" }).click();
    await page.getByRole("link", { name: "Mở bản nháp" }).waitFor();
    assert.equal(calls.filter((c) => c.method !== "GET").length, 0);
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
});
test("background: dismissing keeps tracking and is different from explicit stop; workspace scoped", async () => {
  const { page, errors } = await pageForTest();
  try {
    const state = { status: "compiling", done: 1, total: 4 };
    const calls = await mockTaskApi(page, state);
    await page.evaluate(
      (task) =>
        window.mountTasks([
          task,
          { ...task, id: "foreign", workspaceId: "ws_other" },
        ]),
      backgroundTask,
    );
    await page.getByText("Đã chuẩn bị 1/4 phần").waitFor();
    await page
      .getByRole("button", { name: `Ẩn tác vụ ${backgroundTask.sourceTitle}` })
      .click();
    state.status = "ready";
    await page.waitForFunction(
      () => window.taskStore.getState().tasks[0].status === "ready",
    );
    assert.equal(calls.filter((c) => c.method !== "GET").length, 0);
    assert.equal(calls.filter((c) => c.path.includes("/ws_other/")).length, 0);
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
});

test("background: only an explicit stop sends the cancellation request", async () => {
  const { page, errors } = await pageForTest();
  try {
    const state = { status: "compiling", done: 1, total: 4 };
    const calls = await mockTaskApi(page, state);
    await page.evaluate((task) => window.mountTasks([task]), backgroundTask);
    await page.getByText("Đã chuẩn bị 1/4 phần").waitFor();
    await page
      .getByRole("button", { name: `Dừng xử lý ${backgroundTask.sourceTitle}` })
      .click();
    await page.waitForFunction(
      () => window.taskStore.getState().tasks[0].status === "cancelled",
    );
    assert.equal(
      calls.filter((c) => c.method === "POST" && c.path.endsWith("/cancel"))
        .length,
      1,
    );
    assert.deepEqual(errors, []);
  } finally {
    await page.close();
  }
});
