export function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = [...fileName]
    .map((character) =>
      character.charCodeAt(0) < 32 || character === "/" || character === "\\"
        ? "_"
        : character,
    )
    .join("");
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
