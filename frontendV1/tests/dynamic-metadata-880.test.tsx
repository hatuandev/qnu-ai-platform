// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { v1Client } from "@/app/api/v1";
import { MetadataProposalItem } from "@/features/knowledge/metadata-proposal-item";
import {
  annotationDraftIssues,
  draftsToAnnotations,
  emptyAnnotationDraft,
} from "@/features/knowledge/retrieval-metadata-editor";
import { MetadataFacetFields } from "@/features/rag/metadata-facet-fields";
import {
  draftToFilter,
  filterToDraft,
  isMetadataFilterDraftEmpty,
} from "@/features/rag/metadata-filter-fields";
import {
  DEFAULT_RAG_POLICY_FORM,
  ragPolicyFormSchema,
  toRagPolicy,
  toRagPolicyForm,
} from "@/features/rag/schemas";
import {
  type MetadataScalar,
  NEW_ASSISTANT_RAG_POLICY,
} from "@/features/rag/types";

vi.mock("@/app/auth/v1", () => ({
  useV1Auth: () => ({ sessionId: 880 }),
}));

beforeEach(() => {
  Element.prototype.hasPointerCapture = () => false;
  Element.prototype.scrollIntoView = () => {};
  Element.prototype.releasePointerCapture = () => {};
  vi.stubGlobal("PointerEvent", MouseEvent);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test("assistant editing and turn drafts preserve typed custom scopes", () => {
  const attributes = { Mã: "0012", Số: 12, Bật: false };
  const policy = toRagPolicy(
    ragPolicyFormSchema.parse({
      ...DEFAULT_RAG_POLICY_FORM,
      filter_attributes: attributes,
    }),
  );
  expect(policy.metadata_filter.attributes).toEqual(attributes);
  expect(toRagPolicy(toRagPolicyForm(policy))).toEqual(policy);
  expect(draftToFilter(filterToDraft(policy.metadata_filter))).toEqual({
    attributes,
  });
  expect(
    isMetadataFilterDraftEmpty(filterToDraft(policy.metadata_filter)),
  ).toBe(false);
  expect(isMetadataFilterDraftEmpty(filterToDraft({}))).toBe(true);
  expect(NEW_ASSISTANT_RAG_POLICY.scope_resolution).toBe("catalog");
  expect(toRagPolicyForm(null).scope_resolution).toBe("explicit");
});

test("manual values retain their type and require a source quote", () => {
  const draft = {
    ...emptyAnnotationDraft("paragraph"),
    section: "0",
    paragraph: "0",
    attributeName: "Mã",
    attributeValue: "0012",
    attributeType: "text" as const,
    evidence: [{ id: "one", citation: "ocr:proof", quote: "Mã: 0012" }],
  };
  expect(annotationDraftIssues([draft]).size).toBe(0);
  expect(draftsToAnnotations([draft])[0].values.attributes).toEqual({
    Mã: "0012",
  });
  expect(
    annotationDraftIssues([
      { ...draft, attributeType: "number", attributeValue: "NaN" },
    ]).size,
  ).toBe(1);
  expect(annotationDraftIssues([{ ...draft, evidence: [] }]).size).toBe(1);
});

function Filters() {
  const [attributes, setAttributes] = useState<Record<string, MetadataScalar>>({
    "Đã chọn": "Ngoài danh mục",
  });
  return (
    <>
      <MetadataFacetFields
        workspaceId="ws"
        collectionId="col"
        attributes={attributes}
        onChange={setAttributes}
      />
      <output data-testid="selection">{JSON.stringify(attributes)}</output>
    </>
  );
}

test("actual catalog choices preserve numeric types and a previously pinned value", async () => {
  const get = vi.spyOn(v1Client, "get").mockResolvedValue({
    ready: true,
    attributes: { Mã: ["12", 12], Số: [7], Bật: [false] },
    truncated: false,
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <Filters />
    </QueryClientProvider>,
  );
  const trigger = await screen.findByRole("combobox", { name: "Số" });
  fireEvent.keyDown(trigger, { key: "ArrowDown" });
  fireEvent.click(await screen.findByRole("option", { name: "7" }));
  await waitFor(() =>
    expect(screen.getByTestId("selection").textContent).toBe(
      '{"Đã chọn":"Ngoài danh mục","Số":7}',
    ),
  );
  fireEvent.keyDown(screen.getByRole("combobox", { name: "Mã" }), {
    key: "ArrowDown",
  });
  expect(
    await screen.findByRole("option", { name: "12 (văn bản)" }),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("option", { name: "12 (số/logic)" }));
  expect(screen.getByTestId("selection").textContent).toBe(
    '{"Đã chọn":"Ngoài danh mục","Số":7,"Mã":12}',
  );
  expect(get).toHaveBeenCalledWith(
    "/workspaces/ws/collections/col/search-facets",
    expect.objectContaining({ signal: expect.any(AbortSignal) }),
  );
});

test("a selected proposal can be edited without exposing proof identifiers", async () => {
  const edit = vi.fn();
  render(
    <MetadataProposalItem
      selected
      onSelected={vi.fn()}
      onEdit={edit}
      proposal={{
        id: "a".repeat(64),
        status: "proposed",
        origin: "model",
        annotation: {
          target: "paragraph:0:0",
          values: { attributes: { "Cơ sở": "A" } },
          evidence: [{ citation: "ocr:private-proof", quote: "Cơ sở A" }],
        },
        source: {
          workspace_id: "ws",
          collection_id: "col",
          source_id: "source",
          revision_id: "revision",
          evidence_id: "proof",
          filename: "Synthetic.docx",
          content_type:
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          canonical_sha256: "a".repeat(64),
          manifest_sha256: "b".repeat(64),
          page: 1,
        },
      }}
    />,
  );
  fireEvent.pointerDown(
    screen.getByRole("button", { name: "Thao tác đề xuất" }),
    { button: 0, ctrlKey: false, pointerType: "mouse" },
  );
  fireEvent.click(
    await screen.findByRole("menuitem", { name: "Chỉnh giá trị" }),
  );
  expect(edit).toHaveBeenCalledWith({ value: "A", quote: "Cơ sở A" });
  expect(screen.queryByText("ocr:private-proof")).toBeNull();
});
