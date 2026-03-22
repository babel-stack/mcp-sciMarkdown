"""Detect chapter and section patterns in text and convert to markdown headings."""

import re
import logging

logger = logging.getLogger(__name__)

# Patterns: (regex, heading_level)
_HEADING_PATTERNS = [
    # "Capítulo N. Title" or "Capítulo N: Title" → # heading
    (re.compile(r'^(Cap[ií]tulo\s+\d+[\.:]\s*.+)$', re.IGNORECASE | re.MULTILINE), 1),
    # "Capítol N. Title" (Catalan) → # heading
    (re.compile(r'^(Cap[ií]tol\s+\d+[\.:]\s*.+)$', re.IGNORECASE | re.MULTILINE), 1),
    # "Chapter N. Title" or "Chapter N: Title" → # heading
    (re.compile(r'^(Chapter\s+\d+[\.:]\s*.+)$', re.IGNORECASE | re.MULTILINE), 1),
    # "CAPÍTULO N" all caps → # heading
    (re.compile(r'^(CAP[ÍI]TULO\s+\d+.*)$', re.MULTILINE), 1),
    # "TEMA N" → # heading
    (re.compile(r'^(TEMA\s+[IVXLC\d]+[\.:].*)$', re.MULTILINE), 1),
    # "PROBLEMA I.N" or "Problema N.N" → ## heading
    (re.compile(r'^(PROBLEMA\s+[IVXLC]+\.\d+.*)$', re.MULTILINE), 2),
    (re.compile(r'^(Problema\s+\d+[\.:].*)$', re.IGNORECASE | re.MULTILINE), 2),
    # "N.N.N. Title" → ### heading (must come before N.N. pattern)
    (re.compile(r'^(\d+\.\d+\.\d+\.?\s+[A-ZÁÉÍÓÚÑÇÀ].{3,})$', re.MULTILINE), 3),
    # "N.N. Title" (e.g. "4.3. Ecuación de Euler") → ## heading
    # Must start with number, have a dot-separated section, then text starting with uppercase
    (re.compile(r'^(\d+\.\d+\.\s+[A-ZÁÉÍÓÚÑÇÀ].{3,})$', re.MULTILINE), 2),
    # "PRÓLOGO", "PRESENTACIÓN", "BIBLIOGRAFÍA", "APÉNDICE", "ÍNDICE" → # heading
    (re.compile(r'^(PRÓLOGO|PRESENTACI[ÓO]N|BIBLIOGRAF[ÍI]A|AP[ÉE]NDICE|[ÍI]NDICE(?:\s+ANAL[ÍI]TICO)?)$', re.MULTILINE), 1),
    # "LISTA DE SÍMBOLOS", "LISTA DE FIGURAS", "LISTA DE TABLAS" → ## heading
    (re.compile(r'^(LISTA\s+DE\s+\S+.*)$', re.MULTILINE), 2),
    # "Problemas propuestos" → ## heading
    (re.compile(r'^(Problemas\s+propuestos.*)$', re.IGNORECASE | re.MULTILINE), 2),
]


class HeadingDetector:
    """Detects chapter and section patterns in markdown text and converts them to headings."""

    def process(self, markdown: str) -> str:
        """Convert detected chapter/section patterns to markdown headings.

        Only converts lines that are NOT already headings (don't start with #).
        """
        lines = markdown.split('\n')
        result = []

        for line in lines:
            stripped = line.strip()
            # Skip if already a heading
            if stripped.startswith('#'):
                result.append(line)
                continue

            converted = False
            for pattern, level in _HEADING_PATTERNS:
                m = pattern.match(stripped)
                if m:
                    title = m.group(1).strip()
                    prefix = '#' * level
                    result.append(f'{prefix} {title}')
                    converted = True
                    break

            if not converted:
                result.append(line)

        return '\n'.join(result)
