from scimarkdown.models import EnrichedResult, TextBlock, MathRegion, ImageRef


def test_text_block_creation():
    block = TextBlock(position=0, content="Hello world", block_type="paragraph")
    assert block.position == 0
    assert block.content == "Hello world"
    assert block.block_type == "paragraph"


def test_math_region_creation():
    region = MathRegion(
        position=5,
        original_text="x² + y² = z²",
        latex=r"x^{2} + y^{2} = z^{2}",
        source_type="unicode",
        confidence=0.95,
    )
    assert region.latex == r"x^{2} + y^{2} = z^{2}"
    assert region.source_type == "unicode"
    assert region.confidence == 0.95
    assert region.is_inline is True


def test_math_region_block():
    region = MathRegion(
        position=10,
        original_text="sum formula",
        latex=r"\sum_{i=1}^{n} x_i",
        source_type="omml",
        confidence=1.0,
        is_inline=False,
    )
    assert region.is_inline is False


def test_image_ref_creation():
    ref = ImageRef(
        position=3,
        file_path="doc_img00001.png",
        original_format="png",
        width=800,
        height=600,
        caption="Figure 1: Architecture diagram",
        reference_label="Figure 1",
        ordinal=1,
    )
    assert ref.file_path == "doc_img00001.png"
    assert ref.ordinal == 1
    assert ref.caption == "Figure 1: Architecture diagram"


def test_image_ref_no_reference():
    ref = ImageRef(
        position=7,
        file_path="doc_img00002.png",
        original_format="jpeg",
        width=640,
        height=480,
    )
    assert ref.reference_label is None
    assert ref.ordinal is None
    assert ref.caption is None


def test_enriched_result():
    result = EnrichedResult(
        base_markdown="# Title\n\nSome text",
        title="Title",
        text_blocks=[TextBlock(position=0, content="Title", block_type="heading")],
        images=[],
        math_regions=[],
    )
    assert result.base_markdown == "# Title\n\nSome text"
    assert len(result.text_blocks) == 1
    assert len(result.images) == 0


def test_enriched_result_with_metadata():
    result = EnrichedResult(
        base_markdown="content",
        metadata={"author": "Test", "date": "2026-01-01"},
    )
    assert result.metadata["author"] == "Test"
