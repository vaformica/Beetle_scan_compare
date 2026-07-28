from pathlib import Path

from PIL import Image

from beetle_compare.app import ThumbnailCache


def test_thumbnail_cache_prefetches_and_reuses_image(tmp_path: Path):
    path = tmp_path / "beetle-D.tif"
    Image.new("RGB", (1200, 800), "white").save(path)
    cache = ThumbnailCache(maximum_items=4)
    try:
        cache.prefetch(path, 500, 500)
        first = cache.get(path, 500, 500)
        second = cache.get(path, 500, 500)
        assert first is second
        assert first.width <= 500
        assert first.height <= 500
    finally:
        cache.close()
