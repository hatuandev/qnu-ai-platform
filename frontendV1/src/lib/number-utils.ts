import type React from "react";

const vndFormatter = new Intl.NumberFormat("vi-VN");

/**
 * Lọc sạch mọi ký tự không phải chữ số (0-9)
 */
export function digitsOnly(value: string | undefined | null): string {
  if (!value) return "";
  return value.replace(/\D/g, "");
}

/**
 * Định dạng số thành chuỗi tiền tệ VND có dấu chấm phân cách hàng nghìn (VD: 500000 -> "500.000")
 */
export function formatVnd(value: number | string | undefined | null): string {
  if (value === undefined || value === null || value === "") return "";
  const num = typeof value === "number" ? value : Number(digitsOnly(value));
  if (Number.isNaN(num) || num === 0) return "";
  return vndFormatter.format(num);
}

/**
 * Chuyển chuỗi tiền tệ có dấu phân cách thành số nguyên (VD: "500.000" -> 500000)
 */
export function parseVnd(raw: string | undefined | null): number {
  if (!raw) return 0;
  const digits = digitsOnly(raw);
  if (!digits) return 0;
  return Number(digits);
}

/**
 * Chặn các phím phi số trên thẻ input type="number" hoặc input số nguyên:
 * Chặn 'e', 'E', '+', '-', '.'
 */
export function blockNonNumericKeys(e: React.KeyboardEvent<HTMLInputElement>) {
  if (["e", "E", "+", "-", "."].includes(e.key)) {
    e.preventDefault();
  }
}
