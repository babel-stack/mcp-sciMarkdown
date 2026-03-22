"""Tests for HeadingDetector filter."""

from scimarkdown.filters.heading_detector import HeadingDetector


class TestHeadingDetector:
    def setup_method(self):
        self.detector = HeadingDetector()

    # --- Chapter patterns (level 1) ---

    def test_capitulo_dot(self):
        result = self.detector.process("Capítulo 1. Introducción")
        assert result == "# Capítulo 1. Introducción"

    def test_capitulo_colon(self):
        result = self.detector.process("Capítulo 4: Dinámica de fluidos")
        assert result == "# Capítulo 4: Dinámica de fluidos"

    def test_capitulo_without_accent(self):
        result = self.detector.process("Capitulo 2. Mecánica")
        assert result == "# Capitulo 2. Mecánica"

    def test_capitulo_uppercase(self):
        result = self.detector.process("CAPÍTULO 3")
        assert result == "# CAPÍTULO 3"

    def test_capitulo_uppercase_no_accent(self):
        result = self.detector.process("CAPITULO 5 Fluidos")
        assert result == "# CAPITULO 5 Fluidos"

    def test_chapter_english(self):
        result = self.detector.process("Chapter 3. Methods")
        assert result == "# Chapter 3. Methods"

    def test_chapter_english_colon(self):
        result = self.detector.process("Chapter 1: Introduction")
        assert result == "# Chapter 1: Introduction"

    def test_capitol_catalan(self):
        result = self.detector.process("Capítol 2. Introducció")
        assert result == "# Capítol 2. Introducció"

    def test_capitol_catalan_no_accent(self):
        result = self.detector.process("Capitol 1. Termodinàmica")
        assert result == "# Capitol 1. Termodinàmica"

    def test_tema(self):
        result = self.detector.process("TEMA 3: Termodinámica")
        assert result == "# TEMA 3: Termodinámica"

    def test_tema_roman(self):
        result = self.detector.process("TEMA IV. Fluidos")
        assert result == "# TEMA IV. Fluidos"

    # --- Section patterns (level 2) ---

    def test_numbered_section_dot(self):
        result = self.detector.process("4.3. Ecuación de Euler")
        assert result == "## 4.3. Ecuación de Euler"

    def test_numbered_section_uppercase_start(self):
        result = self.detector.process("1.1. Áreas de aplicación")
        assert result == "## 1.1. Áreas de aplicación"

    def test_problema_roman_dot(self):
        result = self.detector.process("PROBLEMA I.1 Flujo en tubería")
        assert result == "## PROBLEMA I.1 Flujo en tubería"

    def test_problema_lowercase(self):
        result = self.detector.process("Problema 3. Cálculo de presión")
        assert result == "## Problema 3. Cálculo de presión"

    def test_problemas_propuestos(self):
        result = self.detector.process("Problemas propuestos")
        assert result == "## Problemas propuestos"

    def test_problemas_propuestos_with_suffix(self):
        result = self.detector.process("Problemas propuestos del capítulo")
        assert result == "## Problemas propuestos del capítulo"

    def test_lista_de_simbolos(self):
        result = self.detector.process("LISTA DE SÍMBOLOS")
        assert result == "## LISTA DE SÍMBOLOS"

    def test_lista_de_figuras(self):
        result = self.detector.process("LISTA DE FIGURAS")
        assert result == "## LISTA DE FIGURAS"

    def test_lista_de_tablas(self):
        result = self.detector.process("LISTA DE TABLAS")
        assert result == "## LISTA DE TABLAS"

    # --- Subsection patterns (level 3) ---

    def test_numbered_subsection(self):
        result = self.detector.process("4.3.1. Subsección de ejemplo")
        assert result == "### 4.3.1. Subsección de ejemplo"

    def test_numbered_subsection_no_trailing_dot(self):
        result = self.detector.process("2.1.3 Algoritmo de Newton")
        assert result == "### 2.1.3 Algoritmo de Newton"

    # --- Special section headings (level 1) ---

    def test_prologo(self):
        result = self.detector.process("PRÓLOGO")
        assert result == "# PRÓLOGO"

    def test_presentacion(self):
        result = self.detector.process("PRESENTACIÓN")
        assert result == "# PRESENTACIÓN"

    def test_presentacion_no_accent(self):
        result = self.detector.process("PRESENTACION")
        assert result == "# PRESENTACION"

    def test_bibliografia(self):
        result = self.detector.process("BIBLIOGRAFÍA")
        assert result == "# BIBLIOGRAFÍA"

    def test_apendice(self):
        result = self.detector.process("APÉNDICE")
        assert result == "# APÉNDICE"

    def test_indice(self):
        result = self.detector.process("ÍNDICE")
        assert result == "# ÍNDICE"

    def test_indice_analitico(self):
        result = self.detector.process("ÍNDICE ANALÍTICO")
        assert result == "# ÍNDICE ANALÍTICO"

    # --- Already a heading — must not be changed ---

    def test_already_heading_h1(self):
        result = self.detector.process("# Title Already")
        assert result == "# Title Already"

    def test_already_heading_h2(self):
        result = self.detector.process("## Section Already")
        assert result == "## Section Already"

    # --- Normal content — must NOT be converted ---

    def test_normal_paragraph(self):
        text = "Este es un párrafo normal de texto."
        result = self.detector.process(text)
        assert result == text

    def test_standalone_number_not_converted(self):
        result = self.detector.process("42")
        assert result == "42"

    def test_standalone_number_75(self):
        result = self.detector.process("75")
        assert result == "75"

    def test_inline_chapter_reference_not_converted(self):
        """A chapter reference inside a sentence should not be converted."""
        text = "Véase el Capítulo 3 para más detalles."
        result = self.detector.process(text)
        assert result == text

    def test_small_numbered_section_not_converted(self):
        """Short text after number dot should not become a heading."""
        result = self.detector.process("4.3. Hi")
        # 'Hi' is only 2 chars, less than required 3
        assert result == "4.3. Hi"

    # --- Multi-line input ---

    def test_multiline_input(self):
        text = "Capítulo 1. Introducción\n\nNormal paragraph here.\n\n4.3. Ecuación de Euler"
        result = self.detector.process(text)
        assert result == "# Capítulo 1. Introducción\n\nNormal paragraph here.\n\n## 4.3. Ecuación de Euler"

    def test_mixed_headings_and_text(self):
        text = "# Already heading\n\nCapítulo 2. Dinámica\n\nSome content."
        result = self.detector.process(text)
        assert "# Already heading" in result
        assert "# Capítulo 2. Dinámica" in result
        assert "Some content." in result
