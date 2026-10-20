import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  QnuReaderDocument,
  ReaderReference,
  ReaderTable,
} from "@/types/qnu-reader";

function References({ refs }: { refs: ReaderReference[] }) {
  return refs.map((ref) => (
    <sup key={ref.id} id={ref.id} className="ml-1">
      <a
        href={`#${ref.target_id}`}
        className="text-primary underline"
        aria-label={`Đọc chú thích ${ref.label}`}
      >
        [{ref.label}]
      </a>
    </sup>
  ));
}

function SourceTable({ table }: { table: ReaderTable }) {
  const layout = table.layout;
  if (!layout)
    return (
      <Table>
        <TableHeader>
          <TableRow>
            {table.headers.map((header, i) => (
              <TableHead key={table.column_ids[i]}>
                {header || `Cột ${i + 1} (chưa xác định tên)`}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {table.rows.map((row, ri) => (
            <TableRow key={table.row_ids[ri]}>
              {row.map((cell, ci) => (
                <TableCell
                  key={table.column_ids[ci]}
                  className="whitespace-pre-wrap align-top"
                >
                  {cell}
                  <References
                    refs={table.references.filter(
                      (ref) =>
                        ref.block_id === table.row_ids[ri] &&
                        (ref.table?.column ?? 1) === ci + 1,
                    )}
                  />
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    );
  const renderRows = (start: number, end: number, header: boolean) =>
    Array.from({ length: end - start }, (_, n) => {
      const ri = start + n;
      const Cell = header ? TableHead : TableCell;
      return (
        <TableRow key={ri}>
          {layout.cells
            .filter((cell) => cell.row_start === ri)
            .sort((a, b) => a.col_start - b.col_start)
            .map((cell) => (
              <Cell
                key={`${ri}-${cell.col_start}`}
                rowSpan={cell.row_end - cell.row_start}
                colSpan={cell.col_end - cell.col_start}
                className="whitespace-pre-wrap align-top"
              >
                {cell.text}
                <References
                  refs={table.references.filter(
                    (ref) =>
                      ref.table &&
                      ref.table.row > cell.row_start &&
                      ref.table.row <= cell.row_end &&
                      ref.table.column > cell.col_start &&
                      ref.table.column <= cell.col_end,
                  )}
                />
              </Cell>
            ))}
        </TableRow>
      );
    });
  return (
    <div>
      {layout.header_rows === 0 && (
        <p className="text-xs text-muted-foreground mb-2">
          Chưa xác định hàng tiêu đề; giữ nguyên bố cục nguồn.
        </p>
      )}
      <Table>
        {layout.header_rows > 0 && (
          <TableHeader>{renderRows(0, layout.header_rows, true)}</TableHeader>
        )}
        <TableBody>
          {renderRows(layout.header_rows, layout.rows, false)}
        </TableBody>
      </Table>
    </div>
  );
}

function Markdown({
  children,
  references = [],
}: {
  children: string;
  references?: ReaderReference[];
}) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        img: ({ alt }) => (
          <span className="text-muted-foreground">
            {alt ? `[Hình: ${alt}]` : "[Hình trong nguồn]"}
          </span>
        ),
        a: ({ children: label, href }) => {
          const ref = references.find(
            (entry) => href === `#${entry.target_id}--ref--${entry.id}`,
          );
          return ref ? (
            <a
              id={ref.id}
              href={`#${ref.target_id}`}
              className="text-primary underline"
            >
              {label}
            </a>
          ) : href?.startsWith("#qnu-") ? (
            <a href={href} className="text-primary underline">
              {label}
            </a>
          ) : (
            <span>{label}</span>
          );
        },
      }}
    >
      {children}
    </ReactMarkdown>
  );
}

export function QnuDocumentReader({
  document,
}: {
  document: QnuReaderDocument;
}) {
  return (
    <article
      aria-label="Bản đọc tài liệu"
      className="space-y-5 text-sm leading-relaxed break-words [&_h1]:text-xl [&_h1]:font-semibold [&_h2]:text-lg [&_h2]:font-semibold [&_h3]:font-semibold [&_p]:my-2 [&_ul]:list-disc [&_ul]:pl-6 [&_ol]:list-decimal [&_ol]:pl-6 [&_pre]:overflow-auto [&_pre]:rounded-md [&_pre]:bg-muted [&_pre]:p-3"
    >
      {!!document.limitations?.length && (
        <p
          role="note"
          className="rounded-md bg-muted p-3 text-muted-foreground"
        >
          Một số chú thích chưa có liên kết, nội dung hoặc bố cục chắc chắn. Cần
          đối chiếu tài liệu gốc khi sử dụng những phần này.
        </p>
      )}
      {document.blocks.length === 0 && document.notes.length === 0 && (
        <p className="text-muted-foreground">
          Chưa có nội dung để hiển thị trong bản đọc này.
        </p>
      )}
      {document.blocks.map((block) => (
        <section key={block.id} id={block.anchor} className="scroll-mt-6">
          {block.table ? (
            <SourceTable table={block.table} />
          ) : (
            <Markdown references={block.embedded_references}>
              {block.markdown}
            </Markdown>
          )}
          <References refs={block.references} />
        </section>
      ))}
      {document.notes.length > 0 && (
        <section aria-label="Chú thích" className="border-t border-border pt-4">
          <h2 className="font-semibold">Chú thích</h2>
          {document.notes.map((note) => (
            <div key={note.id} id={note.anchor} className="my-3 scroll-mt-6">
              <span className="font-medium">[{note.label}]</span>
              <Markdown>{note.markdown}</Markdown>
              {note.unresolved && (
                <p className="text-xs text-muted-foreground">
                  Vị trí trang hoặc cấu trúc chú thích còn thông tin chưa xác
                  định; xem nguồn gốc khi đối chiếu.
                </p>
              )}
              <div className="flex flex-wrap gap-3">
                {note.anchors.map((ref, i) => (
                  <a
                    key={ref.id}
                    href={`#${ref.id}`}
                    className="text-xs text-primary underline"
                    aria-label={`Quay lại tham chiếu ${i + 1} của chú thích ${note.label}`}
                  >
                    Quay lại{" "}
                    {note.anchors.length > 1 ? i + 1 : "vị trí tham chiếu"}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </section>
      )}
    </article>
  );
}
