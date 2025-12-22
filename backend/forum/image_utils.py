from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from PIL import Image, ImageOps, UnidentifiedImageError


# Max single image size (bytes).
# Product requirement: single image must be <= 20MB.
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000  # hard safety cap
MAX_IMAGE_SIDE = 4096

ALLOWED_MIME = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp',
}


@dataclass(frozen=True)
class ProcessedImage:
    content: ContentFile
    ext: str
    width: int
    height: int


def _is_png_with_alpha(img: Image.Image) -> bool:
    return img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)


def validate_and_process_uploaded_image(*, uploaded_file, field_name: str = 'image') -> ProcessedImage:
    """Validate that the upload is a real image and return a compressed/normalized ContentFile.

    - Max 20MB
    - Only JPEG/PNG/WEBP by MIME
    - EXIF orientation normalized
    - Max side <= 4096 (downscale)
    - Re-encode to reduce size without excessive quality loss
    """

    size = int(getattr(uploaded_file, 'size', 0) or 0)
    if size <= 0:
        raise ValidationError({field_name: 'Empty file.'})
    if size > MAX_IMAGE_BYTES:
        raise ValidationError({field_name: 'Image too large (max 20MB).'})

    content_type = (getattr(uploaded_file, 'content_type', '') or '').lower()
    if content_type not in ALLOWED_MIME:
        raise ValidationError({field_name: 'Only JPEG/PNG/WEBP images are allowed.'})

    raw = uploaded_file.read()
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValidationError({field_name: 'Image too large (max 20MB).'})

    try:
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        img = Image.open(BytesIO(raw))
        img.verify()  # validate structure
        img = Image.open(BytesIO(raw))  # reopen after verify
        img = ImageOps.exif_transpose(img)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValidationError({field_name: 'Invalid or unsafe image file.'})

    width, height = img.size
    if width <= 0 or height <= 0:
        raise ValidationError({field_name: 'Invalid image dimensions.'})

    # Downscale very large images
    max_side = max(width, height)
    if max_side > MAX_IMAGE_SIDE:
        scale = MAX_IMAGE_SIDE / float(max_side)
        new_w = max(1, int(width * scale))
        new_h = max(1, int(height * scale))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        width, height = img.size

    out = BytesIO()

    # Re-encode based on MIME, keeping alpha when needed
    if content_type == 'image/png':
        if _is_png_with_alpha(img):
            img.save(out, format='PNG', optimize=True)
            ext = 'png'
        else:
            img = img.convert('RGB')
            img.save(out, format='JPEG', quality=85, optimize=True, progressive=True)
            ext = 'jpg'
    elif content_type == 'image/webp':
        img = img.convert('RGB') if img.mode not in ('RGB',) else img
        img.save(out, format='WEBP', quality=82, method=6)
        ext = 'webp'
    else:  # jpeg
        img = img.convert('RGB')
        img.save(out, format='JPEG', quality=85, optimize=True, progressive=True)
        ext = 'jpg'

    content = ContentFile(out.getvalue())
    return ProcessedImage(content=content, ext=ext, width=width, height=height)
