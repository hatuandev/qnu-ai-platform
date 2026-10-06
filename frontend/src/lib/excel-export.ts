export interface ExcelColumn<T> {
  header: string;
  accessor: (
    item: T,
    index: number,
  ) => string | number | boolean | null | undefined;
  width?: number;
}

export interface ExcelSheet<T> {
  sheetName: string;
  data: T[];
  columns: ExcelColumn<T>[];
}

/**
 * Exports data to an Excel (.xlsx) file with proper UTF-8 Vietnamese encoding,
 * column headers, and auto-adjusted column widths.
 * Uses dynamic import so that the xlsx bundle is only loaded on-demand.
 */
export async function exportToExcel<T>({
  filename,
  sheetName = "Sheet1",
  data,
  columns,
}: {
  filename: string;
  sheetName?: string;
  data: T[];
  columns: ExcelColumn<T>[];
}) {
  const XLSX = await import("xlsx");
  const formattedRows = data.map((item, index) => {
    const row: Record<string, string | number | boolean> = {};
    for (const col of columns) {
      const val = col.accessor(item, index);
      row[col.header] = val === null || val === undefined ? "" : val;
    }
    return row;
  });

  const worksheet = XLSX.utils.json_to_sheet(formattedRows);

  // Auto-fit column widths
  const colWidths = columns.map((col) => {
    if (col.width) return { wch: col.width };
    let maxLen = col.header.length;
    for (const row of formattedRows) {
      const cellVal = String(row[col.header] ?? "");
      if (cellVal.length > maxLen) {
        maxLen = Math.min(cellVal.length, 50);
      }
    }
    return { wch: Math.max(maxLen + 4, 12) };
  });

  worksheet["!cols"] = colWidths;

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName.slice(0, 31));

  const cleanFilename = filename.endsWith(".xlsx")
    ? filename
    : `${filename}.xlsx`;

  XLSX.writeFile(workbook, cleanFilename);
}

/**
 * Exports multiple datasets into separate sheets in a single Excel (.xlsx) workbook.
 */
export async function exportMultiSheetToExcel({
  filename,
  sheets,
}: {
  filename: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  sheets: ExcelSheet<any>[];
}) {
  const XLSX = await import("xlsx");
  const workbook = XLSX.utils.book_new();

  for (const sheet of sheets) {
    const formattedRows = sheet.data.map((item, index) => {
      const row: Record<string, string | number | boolean> = {};
      for (const col of sheet.columns) {
        const val = col.accessor(item, index);
        row[col.header] = val === null || val === undefined ? "" : val;
      }
      return row;
    });

    const worksheet = XLSX.utils.json_to_sheet(formattedRows);

    const colWidths = sheet.columns.map((col) => {
      if (col.width) return { wch: col.width };
      let maxLen = col.header.length;
      for (const row of formattedRows) {
        const cellVal = String(row[col.header] ?? "");
        if (cellVal.length > maxLen) {
          maxLen = Math.min(cellVal.length, 50);
        }
      }
      return { wch: Math.max(maxLen + 4, 12) };
    });

    worksheet["!cols"] = colWidths;
    XLSX.utils.book_append_sheet(
      workbook,
      worksheet,
      sheet.sheetName.slice(0, 31),
    );
  }

  const cleanFilename = filename.endsWith(".xlsx")
    ? filename
    : `${filename}.xlsx`;

  XLSX.writeFile(workbook, cleanFilename);
}
