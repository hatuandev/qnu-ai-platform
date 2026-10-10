/**
 * Quản lý kho Idempotency Key ổn định gắn liền với từng đối tượng File qua WeakMap.
 *
 * Quy tắc:
 * 1. Cùng một đối tượng File trong cùng một phiên modal luôn nhận cùng một UUID khi retry.
 * 2. Không sinh lại UUID mới mỗi lần bấm nút tải lên.
 * 3. Hai đối tượng File khác nhau luôn nhận hai UUID độc lập (không dựa trên tên file).
 * 4. Khi reset form hoặc đóng modal, kho key được khởi tạo lại (reset).
 */
export class FileIdempotencyManager {
  private map: WeakMap<File, string>;

  constructor() {
    this.map = new WeakMap<File, string>();
  }

  /**
   * Lấy Idempotency Key hiện có hoặc tạo mới nếu chưa tồn tại cho đối tượng File này.
   */
  getOrCreate(file: File): string {
    let key = this.map.get(file);
    if (!key) {
      key = crypto.randomUUID();
      this.map.set(file, key);
    }
    return key;
  }

  /**
   * Khởi tạo lại kho lưu trữ khi modal đóng hoặc người dùng hủy danh sách tệp.
   */
  reset(): void {
    this.map = new WeakMap<File, string>();
  }
}
