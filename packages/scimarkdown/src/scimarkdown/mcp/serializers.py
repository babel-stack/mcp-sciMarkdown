"""Serializers: convert SciMarkdown model objects to plain dicts for JSON output."""

from scimarkdown.models import ImageRef, MathRegion


def math_region_to_dict(region: MathRegion) -> dict:
    """Serialize a MathRegion to a JSON-compatible dict.

    Args:
        region: MathRegion instance to serialize.

    Returns:
        Dict with all fields of the MathRegion.
    """
    return {
        "position": region.position,
        "original_text": region.original_text,
        "latex": region.latex,
        "source_type": region.source_type,
        "confidence": region.confidence,
        "is_inline": region.is_inline,
    }


def image_ref_to_dict(image_ref: ImageRef) -> dict:
    """Serialize an ImageRef to a JSON-compatible dict.

    Args:
        image_ref: ImageRef instance to serialize.

    Returns:
        Dict with all fields of the ImageRef.
    """
    return {
        "position": image_ref.position,
        "file_path": image_ref.file_path,
        "original_format": image_ref.original_format,
        "width": image_ref.width,
        "height": image_ref.height,
        "caption": image_ref.caption,
        "reference_label": image_ref.reference_label,
        "ordinal": image_ref.ordinal,
        "context_text": image_ref.context_text,
    }
