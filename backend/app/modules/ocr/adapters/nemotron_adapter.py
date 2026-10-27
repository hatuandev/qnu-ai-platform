"""Nemotron Parse OpenAI-compatible image inference with located raw evidence."""

import asyncio
import base64
import io
from typing import Any
from urllib.parse import urlsplit

import httpx
from PIL import Image

from app.core.exceptions import AppException
from app.modules.ocr.adapters.base import BaseOCRAdapter
from app.modules.ocr.adapters.nemotron_layout import parse_layout

_PROMPT = '</s><s><predict_bbox><predict_classes><output_markdown><predict_text_in_pic>'


class NemotronParseAdapter(BaseOCRAdapter):
    """One request per image, no cloud fallback or automatic resend."""

    def __init__(self, *, base_url: str | None = None, model_name: str = 'nemotron-parse',
                 api_key: str | None = None, timeout: float = 90, max_tokens: int = 8192) -> None:
        self._base_url = (base_url or '').rstrip('/')
        self._model_name, self._api_key = model_name, api_key
        self._timeout, self._max_tokens = timeout, max_tokens

    @property
    def name(self) -> str:
        return 'nemotron_parse'

    @property
    def display_name(self) -> str:
        return f'Nemotron Parse ({self._model_name})'

    @property
    def model_name(self) -> str:
        return self._model_name

    def is_available(self) -> bool:
        parsed = urlsplit(self._base_url)
        return bool(parsed.scheme in {'http', 'https'} and parsed.hostname
                    and not (parsed.username or parsed.password or parsed.query or parsed.fragment))

    def _endpoint(self) -> str:
        if not self.is_available():
            raise AppException('Nemotron chưa có địa chỉ server hợp lệ.',
                               code='OCR_PROVIDER_UNAVAILABLE', status_code=503)
        if self._base_url.endswith('/v1/chat/completions'):
            return self._base_url
        return self._base_url.removesuffix('/v1') + '/v1/chat/completions'

    async def _request_page(self, content: bytes, mime: str) -> dict[str, Any]:
        payload = {'model': self._model_name, 'messages': [{'role': 'user', 'content': [
            {'type': 'text', 'text': _PROMPT}, {'type': 'image_url', 'image_url': {
                'url': f'data:{mime};base64,' + base64.b64encode(content).decode('ascii')}}]}],
            'max_tokens': self._max_tokens, 'temperature': 0, 'repetition_penalty': 1.1,
            'top_k': 1, 'skip_special_tokens': False}
        headers = {'Authorization': f'Bearer {self._api_key}'} if self._api_key else {}
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as client:
                response = await client.post(self._endpoint(), json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise AppException('Nemotron quá thời gian phản hồi.', code='OCR_SERVICE_TIMEOUT', status_code=504) from exc
        except httpx.RequestError as exc:
            raise AppException('Không kết nối được Nemotron.', code='OCR_SERVICE_UNAVAILABLE', status_code=502) from exc
        if response.status_code != 200:
            code = {401: 'OCR_PROVIDER_AUTH_FAILED', 403: 'OCR_PROVIDER_AUTH_FAILED',
                    429: 'OCR_PROVIDER_RATE_LIMITED'}.get(response.status_code, 'OCR_INFERENCE_ERROR')
            raise AppException(f'Nemotron phản hồi HTTP {response.status_code}.', code=code, status_code=502) from httpx.HTTPStatusError(
                'Nemotron provider HTTP failure', request=response.request, response=response)
        try:
            data = response.json()
            choice = data['choices'][0]
            text = choice['message']['content']
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AppException('Phản hồi Nemotron không hợp lệ.', code='OCR_RESPONSE_INVALID', status_code=502) from exc
        if choice.get('finish_reason') == 'length':
            raise AppException('Đầu ra Nemotron bị cắt; chưa đủ bằng chứng toàn trang.',
                               code='OCR_OUTPUT_TRUNCATED', status_code=422)
        if choice.get('finish_reason') != 'stop' or not isinstance(text, str) or not text.strip():
            raise AppException('Nemotron chưa hoàn tất nhận dạng trang.', code='OCR_RESPONSE_INVALID', status_code=502)
        return data

    @staticmethod
    def _images(content: bytes, filename: str) -> list[tuple[bytes, dict[str, int]]]:
        if filename.lower().endswith('.pdf'):
            import pymupdf
            with pymupdf.open(stream=content, filetype='pdf') as document:
                result = []
                for page in document:
                    pix = page.get_pixmap(dpi=144, alpha=False)
                    result.append((pix.tobytes('png'), {'width': pix.width, 'height': pix.height}))
                return result
        with Image.open(io.BytesIO(content)) as image:
            if getattr(image, 'n_frames', 1) != 1:
                raise AppException('Ảnh nhiều khung cần tách trang trước OCR.', code='OCR_INPUT_UNSUPPORTED', status_code=422)
            output = io.BytesIO()
            image.convert('RGB').save(output, format='PNG')
            return [(output.getvalue(), {'width': image.width, 'height': image.height})]

    async def extract(self, content: bytes, filename: str) -> dict[str, Any]:
        from app.core.provider_capacity import provider_slot
        if not content:
            raise AppException('Tệp nguồn rỗng.', code='DOCUMENT_CONTENT_EMPTY', status_code=400)
        endpoint = self._endpoint()
        images = await asyncio.to_thread(self._images, content, filename)
        if not images:
            raise AppException('Tài liệu không có trang.', code='OCR_CONTENT_EMPTY', status_code=422)
        pages, raw_pages = [], []
        for index, (image, dimensions) in enumerate(images, 1):
            async with provider_slot('ocr', endpoint.lower(), self._timeout):
                data = await self._request_page(image, 'image/png')
            page = parse_layout(data['choices'][0]['message']['content'], index)
            page['dimensions'] = dimensions
            pages.append(page)
            raw_pages.append({'page_number': index, 'dimensions': dimensions, 'response': data})
        return {'engine_used': self.name, 'total_pages': len(pages), 'pages': pages,
                'raw_payload': {'model': self._model_name, 'pages': raw_pages,
                    'request_config': {'max_tokens': self._max_tokens, 'temperature': 0,
                        'repetition_penalty': 1.1, 'top_k': 1, 'skip_special_tokens': False}},
                'raw_text': '\n\n'.join(p['extracted_text'] for p in pages),
                'overall_confidence': 0.0, 'confidence_source': 'unavailable'}
