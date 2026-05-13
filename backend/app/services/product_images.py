"""Generate and cache product images for the commerce catalog."""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import httpx
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger
from app.models.commerce import Product

logger = get_logger(__name__)


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _output_dir() -> Path:
    path = Path(settings.PRODUCT_IMAGE_OUTPUT_DIR)
    if not path.is_absolute():
        path = (_workspace_root() / "backend" / path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _public_url(filename: str) -> str:
    return f"{settings.PRODUCT_IMAGE_PUBLIC_PATH.rstrip('/')}/{filename}"


def _filename(product: Product) -> str:
    seed = f"{product.id}:{product.name}:{product.description}:{product.price}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"product-{product.id}-{digest}.png"


def has_generated_product_image(product: Product) -> bool:
    image_urls = product.image_urls or []
    return any(url.startswith(settings.PRODUCT_IMAGE_PUBLIC_PATH.rstrip("/") + "/") for url in image_urls)


def build_product_image_prompt(product: Product) -> str:
    tags = ", ".join(product.tags or [])
    return (
        "Create a realistic ecommerce product photo for a modern Chinese AI lifestyle recommendation app. "
        "Use a clean light background, soft studio lighting, cute but realistic styling, and no text, logo, "
        "watermark, price tag, or packaging claims. "
        f"Product name: {product.name}. "
        f"Description: {product.description or 'practical lifestyle product'}. "
        f"Tags: {tags or 'lifestyle, travel, shopping'}."
    )


async def generate_product_image(product: Product) -> str:
    """Generate a product image once and return its public URL.

    If the cached file already exists, no model call is made.
    """
    filename = _filename(product)
    output_path = _output_dir() / filename
    if output_path.exists() and output_path.stat().st_size > 0:
        return _public_url(filename)

    if not settings.IMAGE_API_KEY:
        raise RuntimeError("IMAGE_API_KEY is not configured")

    client = AsyncOpenAI(
        api_key=settings.IMAGE_API_KEY,
        base_url=settings.IMAGE_API_BASE,
        timeout=90,
    )
    result = await client.images.generate(
        model=settings.IMAGE_MODEL,
        prompt=build_product_image_prompt(product),
        size="1024x1024",
    )
    image = result.data[0] if result.data else None
    if not image:
        raise RuntimeError("Image API returned no image")

    if image.b64_json:
        output_path.write_bytes(base64.b64decode(image.b64_json))
    elif image.url:
        async with httpx.AsyncClient(timeout=45) as http:
            response = await http.get(image.url)
            response.raise_for_status()
            output_path.write_bytes(response.content)
    else:
        raise RuntimeError("Image API returned no usable payload")

    logger.info("Generated product image for product_id=%s at %s", product.id, output_path)
    return _public_url(filename)
