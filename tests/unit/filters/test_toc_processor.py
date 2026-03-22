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
