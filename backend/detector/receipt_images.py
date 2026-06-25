"""Prepare receipt screenshots for vision LLM (resize / normalize)."""
import mimetypes
from io import BytesIO

from PIL import Image, ImageOps

_RECEIPT_MIME_TYPES = frozenset({
    'image/jpeg', 'image/jpg', 'image/png', 'image/webp',
})

# GMS proxy rejects large generateContent JSON bodies (~90KB+) with a misleading
# "GenerateContentRequest.contents: contents is not specified" error (not a real
# missing-field issue). Keep each image small after base64.
_MAX_EDGE = 1280
_MAX_BYTES = 48_000


def resolve_receipt_mime(upload, raw: bytes) -> str | None:
    content_type = (getattr(upload, 'content_type', None) or '').split(';')[0].strip().lower()
    if content_type in _RECEIPT_MIME_TYPES:
        return 'image/jpeg' if content_type == 'image/jpg' else content_type

    name = getattr(upload, 'name', None) or ''
    guessed, _ = mimetypes.guess_type(name)
    if guessed:
        guessed = guessed.lower()
        if guessed in _RECEIPT_MIME_TYPES:
            return 'image/jpeg' if guessed == 'image/jpg' else guessed

    if raw[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image/png'
    if raw[:2] == b'\xff\xd8':
        return 'image/jpeg'
    if len(raw) >= 12 and raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
        return 'image/webp'
    return None


def _save_jpeg_under_limit(img: Image.Image, max_bytes: int) -> bytes:
    working = img
    edge = min(max(working.size), _MAX_EDGE)

    while edge >= 480:
        if max(working.size) > edge:
            resized = working.copy()
            resized.thumbnail((edge, edge), Image.Resampling.LANCZOS)
        else:
            resized = working

        quality = 82
        while quality >= 35:
            out = BytesIO()
            resized.save(out, format='JPEG', quality=quality, optimize=True)
            data = out.getvalue()
            if len(data) <= max_bytes:
                return data
            quality -= 8

        edge = int(edge * 0.82)

    out = BytesIO()
    working.thumbnail((480, 480), Image.Resampling.LANCZOS)
    working.save(out, format='JPEG', quality=35, optimize=True)
    return out.getvalue()


def prepare_receipt_image(raw: bytes, mime: str) -> tuple[bytes, str]:
    """Downscale and compress so GMS vision API accepts phone screenshots."""
    try:
        img = Image.open(BytesIO(raw))
        img = ImageOps.exif_transpose(img)
    except Exception:
        if len(raw) <= _MAX_BYTES:
            return raw, mime or 'image/jpeg'
        raise ValueError('이미지를 처리할 수 없습니다. 다른 스크린샷을 사용해 주세요.')

    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        base = Image.new('RGB', img.size, (255, 255, 255))
        converted = img.convert('RGBA')
        base.paste(converted, mask=converted.split()[-1])
        img = base
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    return _save_jpeg_under_limit(img, _MAX_BYTES), 'image/jpeg'
