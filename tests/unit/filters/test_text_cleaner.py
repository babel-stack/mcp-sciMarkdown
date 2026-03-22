"""Tests for TextCleaner filter."""

from scimarkdown.filters.text_cleaner import TextCleaner


class TestCleanCid:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_single_cid_removed(self):
        result = self.cleaner.clean_cid("Hello(cid:3)World")
        assert result == "HelloWorld"

    def test_multiple_cids_removed(self):
        result = self.cleaner.clean_cid("(cid:131)(cid:135) text")
        assert result == " text"

    def test_cid_with_large_number(self):
        result = self.cleaner.clean_cid("test(cid:9999)end")
        assert result == "testend"

    def test_no_cid_unchanged(self):
        text = "Normal text without any cid artifacts."
        result = self.cleaner.clean_cid(text)
        assert result == text

    def test_cid_in_middle_of_word(self):
        result = self.cleaner.clean_cid("fl(cid:3)uid")
        assert result == "fluid"

    def test_multiple_cids_on_line(self):
        result = self.cleaner.clean_cid("a(cid:1)b(cid:2)c(cid:3)d")
        assert result == "abcd"

    def test_empty_string(self):
        result = self.cleaner.clean_cid("")
        assert result == ""


class TestNormalizeImagePaths:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_absolute_path_converted(self):
        result = self.cleaner.normalize_image_paths(
            "![alt](/home/u680912/0-Advecta/project/img.png)"
        )
        assert result == "![alt](img.png)"

    def test_absolute_path_no_alt(self):
        result = self.cleaner.normalize_image_paths(
            "![](/home/u680912/path/to/figure.png)"
        )
        assert result == "![](figure.png)"

    def test_relative_path_unchanged(self):
        result = self.cleaner.normalize_image_paths(
            "![caption](relative.png)"
        )
        assert result == "![caption](relative.png)"

    def test_relative_subdir_converted(self):
        result = self.cleaner.normalize_image_paths(
            "![fig](subdir/image.png)"
        )
        # Has no leading slash but has slash — extracts filename
        assert result == "![fig](image.png)"

    def test_multiple_images_in_text(self):
        text = "![a](/path/one.png) and ![b](/path/two.jpg)"
        result = self.cleaner.normalize_image_paths(text)
        assert result == "![a](one.png) and ![b](two.jpg)"

    def test_filename_with_spaces(self):
        result = self.cleaner.normalize_image_paths(
            "![fig](/home/user/my figure.png)"
        )
        assert result == "![fig](my figure.png)"

    def test_filename_with_special_chars(self):
        result = self.cleaner.normalize_image_paths(
            "![fig](/home/user/fig_1-a.png)"
        )
        assert result == "![fig](fig_1-a.png)"

    def test_deep_nested_path(self):
        result = self.cleaner.normalize_image_paths(
            "![x](/a/b/c/d/e/image.jpeg)"
        )
        assert result == "![x](image.jpeg)"

    def test_no_images_unchanged(self):
        text = "Just some text with no images."
        result = self.cleaner.normalize_image_paths(text)
        assert result == text


class TestCleanEmptyLines:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_four_newlines_collapsed(self):
        result = self.cleaner.clean_empty_lines("a\n\n\n\nb")
        assert result == "a\n\n\nb"

    def test_five_newlines_collapsed(self):
        result = self.cleaner.clean_empty_lines("a\n\n\n\n\nb")
        assert result == "a\n\n\nb"

    def test_three_newlines_unchanged(self):
        result = self.cleaner.clean_empty_lines("a\n\n\nb")
        assert result == "a\n\n\nb"

    def test_two_newlines_unchanged(self):
        result = self.cleaner.clean_empty_lines("a\n\nb")
        assert result == "a\n\nb"

    def test_no_extra_newlines_unchanged(self):
        text = "Normal paragraph.\n\nAnother paragraph."
        result = self.cleaner.clean_empty_lines(text)
        assert result == text


class TestCleanIntraParagraphBreaks:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_merges_wrapped_lines(self):
        text = "line one\nline two\nline three"
        result = self.cleaner.clean_intra_paragraph_breaks(text)
        assert result == "line one line two line three"

    def test_preserves_paragraph_breaks(self):
        text = "Para one line a\nline b\n\nPara two line c\nline d"
        result = self.cleaner.clean_intra_paragraph_breaks(text)
        assert result == "Para one line a line b\n\nPara two line c line d"

    def test_preserves_heading_line_but_merges_body(self):
        text = "# Heading\nline one\nline two"
        result = self.cleaner.clean_intra_paragraph_breaks(text)
        assert result == "# Heading\nline one line two"

    def test_heading_alone_unchanged(self):
        text = "# Just a Heading"
        result = self.cleaner.clean_intra_paragraph_breaks(text)
        assert result == "# Just a Heading"

    def test_preserves_list_items(self):
        text = "- item one\n- item two\n- item three"
        result = self.cleaner.clean_intra_paragraph_breaks(text)
        assert result == "- item one\n- item two\n- item three"

    def test_preserves_numbered_list(self):
        text = "1. first\n2. second\n3. third"
        result = self.cleaner.clean_intra_paragraph_breaks(text)
        assert result == "1. first\n2. second\n3. third"

    def test_preserves_star_list(self):
        text = "* item a\n* item b"
        result = self.cleaner.clean_intra_paragraph_breaks(text)
        assert result == "* item a\n* item b"

    def test_preserves_tables(self):
        text = "| col1 | col2 |\n| a | b |"
        result = self.cleaner.clean_intra_paragraph_breaks(text)
        assert result == "| col1 | col2 |\n| a | b |"

    def test_preserves_images(self):
        text = "![alt](img.png)\nsome text"
        result = self.cleaner.clean_intra_paragraph_breaks(text)
        assert result == "![alt](img.png)\nsome text"

    def test_preserves_code_blocks(self):
        text = "```python\ndef foo():\n    pass\n```"
        result = self.cleaner.clean_intra_paragraph_breaks(text)
        assert result == text

    def test_empty_string(self):
        assert self.cleaner.clean_intra_paragraph_breaks("") == ""

    def test_real_world_pdf_wrapping(self):
        text = (
            "Se autoriza la reproducción de esta publicación con fines\n"
            "educativos y otros que no sean comerciales sin permiso\n"
            "escrito previo detentar el derecho de autor, mencionando la cita."
        )
        result = self.cleaner.clean_intra_paragraph_breaks(text)
        assert "\n" not in result
        assert "fines educativos" in result

    def test_mixed_content(self):
        text = (
            "# Heading\n\n"
            "Wrapped line one\nline two\n\n"
            "- list item\n\n"
            "| a | b |\n| c | d |"
        )
        result = self.cleaner.clean_intra_paragraph_breaks(text)
        assert "# Heading" in result
        assert "Wrapped line one line two" in result
        assert "- list item" in result
        assert "| a | b |\n| c | d |" in result


class TestProcess:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def test_process_runs_all_steps(self):
        text = "(cid:3)Hello\n\n\n\n![fig](/abs/path/img.png)"
        result = self.cleaner.process(text)
        assert "(cid:3)" not in result
        assert "img.png" in result
        assert "/abs/path/" not in result
        # 4 newlines collapsed to 3
        assert "\n\n\n\n" not in result

    def test_process_normal_text_unchanged(self):
        text = "Normal markdown content.\n\nAnother paragraph."
        result = self.cleaner.process(text)
        assert result == text

    def test_process_does_not_merge_lines(self):
        """Line merging is NOT part of process() — it runs separately after noise filtering."""
        text = "First line of para\nsecond line of para"
        result = self.cleaner.process(text)
        assert result == text  # Lines preserved for noise filter to work on
