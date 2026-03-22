from scimarkdown.filters.toc_processor import TocProcessor


class TestParseTocEntry:
    """Test parsing individual TOC lines into (title, page_number)."""

    def test_dots_filler(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Chapter 1: Introduction ......... 15")
        assert title == "Chapter 1: Introduction"
        assert page == 15

    def test_spaces_filler(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Chapter 2: Methods                    23")
        assert title == "Chapter 2: Methods"
        assert page == 23

    def test_dashes_filler(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Chapter 3: Results ----------- 45")
        assert title == "Chapter 3: Results"
        assert page == 45

    def test_underscores_filler(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Chapter 4: Discussion _______ 67")
        assert title == "Chapter 4: Discussion"
        assert page == 67

    def test_no_filler_just_spaces(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Appendix A   89")
        assert title == "Appendix A"
        assert page == 89

    def test_roman_numeral_page(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Preface ......... iii")
        assert title == "Preface"
        assert page == "iii"

    def test_section_numbering(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("  3.2.1 Experimental Setup .... 112")
        assert title == "3.2.1 Experimental Setup"
        assert page == 112

    def test_spanish_toc(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("Capítulo 5: Conclusiones ......... 89")
        assert title == "Capítulo 5: Conclusiones"
        assert page == 89

    def test_not_a_toc_entry(self):
        proc = TocProcessor()
        result = proc.parse_entry("This is a normal paragraph without page numbers.")
        assert result is None

    def test_not_a_toc_number_in_middle(self):
        proc = TocProcessor()
        result = proc.parse_entry("In equation 42 we see the result clearly.")
        assert result is None

    def test_indented_subentry(self):
        proc = TocProcessor()
        title, page = proc.parse_entry("    2.1 Background .... 18")
        assert title == "2.1 Background"
        assert page == 18


class TestGenerateSlug:
    def test_simple_title(self):
        proc = TocProcessor()
        assert proc.generate_slug("Introduction") == "introduction"

    def test_title_with_spaces(self):
        proc = TocProcessor()
        assert proc.generate_slug("Chapter 1: Introduction") == "chapter-1-introduction"

    def test_title_with_accents(self):
        proc = TocProcessor()
        slug = proc.generate_slug("Capítulo 5: Conclusiones")
        assert "capítulo" in slug or "capitulo" in slug

    def test_section_number_stripped(self):
        proc = TocProcessor()
        assert proc.generate_slug("3.2.1 Experimental Setup") == "experimental-setup"

    def test_special_chars_removed(self):
        proc = TocProcessor()
        slug = proc.generate_slug("Results & Discussion (Final)")
        assert "&" not in slug
        assert "(" not in slug


class TestDetectTocRegion:
    def test_detect_simple_toc(self):
        proc = TocProcessor()
        md = (
            "# Table of Contents\n"
            "\n"
            "Chapter 1 ......... 1\n"
            "Chapter 2 ......... 15\n"
            "Chapter 3 ......... 30\n"
            "Chapter 4 ......... 45\n"
            "\n"
            "# Chapter 1\n"
            "\n"
            "Content starts here."
        )
        region = proc.detect_toc_region(md)
        assert region is not None
        start, end = region
        assert end - start >= 4

    def test_no_toc(self):
        proc = TocProcessor()
        md = "# Title\n\nJust a normal document.\n\nWith paragraphs."
        assert proc.detect_toc_region(md) is None

    def test_less_than_3_entries_not_toc(self):
        proc = TocProcessor()
        md = "Chapter 1 .... 1\nChapter 2 .... 2\nNormal text."
        assert proc.detect_toc_region(md) is None


class TestProcess:
    def test_full_toc_conversion(self):
        proc = TocProcessor()
        md = (
            "# Índice\n"
            "\n"
            "Introducción ......... 1\n"
            "Capítulo 1: Fundamentos ......... 15\n"
            "Capítulo 2: Métodos ......... 30\n"
            "Conclusiones ......... 89\n"
            "\n"
            "# Introducción\n"
            "\n"
            "This is the introduction."
        )
        result = proc.process(md)
        assert "[Introducción](#introducción)" in result or "[Introducción](#introduccion)" in result
        assert "........." not in result
        assert " 15" not in result.split("\n")[3]  # Page number removed
        assert " 30" not in result.split("\n")[4]

    def test_preserves_non_toc_content(self):
        proc = TocProcessor()
        md = (
            "Chapter 1 .... 1\n"
            "Chapter 2 .... 2\n"
            "Chapter 3 .... 3\n"
            "\n"
            "# Chapter 1\n"
            "\n"
            "Real content paragraph with numbers like 42 and references."
        )
        result = proc.process(md)
        assert "Real content paragraph" in result
        assert "42" in result

    def test_indented_subentries(self):
        proc = TocProcessor()
        md = (
            "Chapter 1 ......... 1\n"
            "  1.1 Background ......... 3\n"
            "  1.2 Theory ......... 7\n"
            "Chapter 2 ......... 15\n"
        )
        result = proc.process(md)
        assert "[Chapter 1]" in result
        assert "[Background]" in result or "[1.1 Background]" in result

    def test_no_toc_returns_unchanged(self):
        proc = TocProcessor()
        md = "# Title\n\nNormal document content."
        assert proc.process(md) == md
