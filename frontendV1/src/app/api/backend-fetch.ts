/** Outbound boundary for the standalone KTX reference; no backend is connected. */
export class TemplateRequestError extends Error {
  constructor() {
    super(
      "Bản mẫu KTX chưa kết nối API. Dữ liệu và thao tác cần backend chưa khả dụng.",
    );
    this.name = "TemplateRequestError";
  }
}

export async function backendFetch(
  ..._args: Parameters<typeof fetch>
): Promise<Response> {
  throw new TemplateRequestError();
}
