"""Direct Word backend: source locators and cached fields, never Office/PDF rendering."""

from io import BytesIO

from docling.backend.msword_backend import MsWordDocumentBackend
from docling.datamodel.backend_options import MsWordBackendOptions
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, WordFormatOption
from docling_core.types.io import DocumentStream

from qnu.platform.errors import AppException


class SourceWordBackend(MsWordDocumentBackend):
    """Disable Docling's optional Office rendering, including its image fallback."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.docx_to_pdf_converter_init = True
        self.locators = {}
        self.table_sources = {}
        self.picture_sources = {}
        self._pending_picture = None
        self.unrendered_drawings = False

    def _convert_elements_via_docx(self, *args, **kwargs) -> None:
        self.unrendered_drawings = True

    def _get_image_from_relationship(self, element, attr, image_type="image"):
        owner = getattr(self, "current_part", self.docx_obj.part)
        relation = owner.rels.get(element.get(attr))
        if relation is not None and relation.is_external:
            self._pending_picture = None
            self.unrendered_drawings = True
            return None
        data = super()._get_image_from_relationship(element, attr, image_type)
        self._pending_picture = None
        if data and relation is not None:
            part = relation.target_part
            self._pending_picture = (
                data,
                part.content_type,
                {**self._locator(element), "image_part": str(part.partname).lstrip("/")},
            )
        return data

    def _add_picture_to_doc(self, doc, parent, pil_image, is_spacer=False):
        ref = super()._add_picture_to_doc(doc, parent, pil_image, is_spacer)
        if self._pending_picture is not None:
            self.picture_sources[ref.cref] = self._pending_picture
            self._pending_picture = None
        return ref

    def _walk_linear(self, body, doc):
        # This branch may contain shapes without an embedded raster asset.
        if body is not None and body.xpath(".//w:drawing") and not self.unrendered_drawings:
            self.unrendered_drawings = any(
                not drawing.xpath(".//a:blip | .//c:chart | .//w:txbxContent")
                for drawing in body.xpath(".//w:drawing")
            )
        return super()._walk_linear(body, doc)

    def _locator(self, element):
        root = element.getroottree().getroot()
        for part in self.docx_obj.part.package.parts:
            if getattr(part, "_element", None) is root:
                return {
                    "format": "docx",
                    "part": str(part.partname).lstrip("/"),
                    "path": element.getroottree().getpath(element),
                }
        raise AppException(
            "Không xác định được vị trí trong gói DOCX.",
            code="docx_source_mapping_invalid",
            status_code=422,
        )

    def _handle_tables(self, element, doc):
        before = len(doc.tables)
        refs = super()._handle_tables(element, doc)
        if len(doc.tables) > before and doc.tables[before].self_ref not in self.locators:
            # The first table is this element; nested tables have their own call.
            item = doc.tables[before]
            self.locators[item.self_ref] = self._locator(element)
            self.table_sources[item.self_ref] = element
        return refs

    def _handle_chart(self, doc, chart_el):
        ref = super()._handle_chart(doc, chart_el)
        if ref:
            self.locators[ref.cref] = self._locator(chart_el)
        return ref

    def convert(self):
        document = super().convert()
        for paragraph, refs in self.paragraph_to_items.items():
            for ref in refs:
                self.locators[ref.cref] = self._locator(paragraph)
        return document


def read_docling(payload: bytes):
    """Use the installed, pinned Word parser only. No model downloads or network."""
    option = WordFormatOption(
        backend=SourceWordBackend,
        backend_options=MsWordBackendOptions(render_chart_images=False),
    )
    try:
        result = DocumentConverter(
            allowed_formats=[InputFormat.DOCX], format_options={InputFormat.DOCX: option}
        ).convert(DocumentStream(name="source.docx", stream=BytesIO(payload)))
    except AppException:
        raise
    except Exception as exc:
        raise AppException(
            "Docling không đọc được cấu trúc DOCX; chưa tạo bản bóc tách.",
            code="docx_source_invalid",
            status_code=422,
        ) from exc
    if result.status.value != "success":
        raise AppException(
            "Docling chưa đọc đầy đủ DOCX.",
            code="docx_source_incomplete",
            status_code=422,
        )
    return result.document, result.input._backend
