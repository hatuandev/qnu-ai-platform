import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { FileIdempotencyManager } from "./idempotency";

describe("FileIdempotencyManager", () => {
  it("trả về cùng một Idempotency Key khi cùng một File được gọi nhiều lần (idempotent retry)", () => {
    const manager = new FileIdempotencyManager();
    const file = new File(
      ["nội dung tài liệu tuyển sinh"],
      "tuyen_sinh_2026.pdf",
      {
        type: "application/pdf",
      },
    );

    const key1 = manager.getOrCreate(file);
    const key2 = manager.getOrCreate(file);
    const key3 = manager.getOrCreate(file);

    assert.ok(key1, "Key phải là chuỗi không rỗng");
    assert.equal(key1, key2, "Lần gọi thứ hai phải trả về đúng key ban đầu");
    assert.equal(key1, key3, "Lần gọi thứ ba phải trả về đúng key ban đầu");
  });

  it("cấp hai Idempotency Key độc lập cho hai đối tượng File khác nhau (kể cả khi trùng tên)", () => {
    const manager = new FileIdempotencyManager();
    const fileA = new File(["nội dung A"], "tailieu.pdf", {
      type: "application/pdf",
    });
    const fileB = new File(["nội dung B"], "tailieu.pdf", {
      type: "application/pdf",
    });

    const keyA = manager.getOrCreate(fileA);
    const keyB = manager.getOrCreate(fileB);

    assert.notEqual(
      keyA,
      keyB,
      "Hai đối tượng File riêng biệt phải có hai UUID độc lập",
    );
  });

  it("cấp Idempotency Key mới cho đối tượng File sau khi gọi reset() (ví dụ đóng hoặc mở lại modal)", () => {
    const manager = new FileIdempotencyManager();
    const file = new File(["nội dung ban đầu"], "van_ban.pdf", {
      type: "application/pdf",
    });

    const keyBefore = manager.getOrCreate(file);
    assert.ok(keyBefore);

    // Người dùng đóng modal hoặc xóa danh sách tệp -> reset
    manager.reset();

    const keyAfter = manager.getOrCreate(file);
    assert.ok(keyAfter);
    assert.notEqual(
      keyBefore,
      keyAfter,
      "Sau khi reset form, File phải được cấp Idempotency Key mới cho phiên nạp tiếp theo",
    );
  });
});
