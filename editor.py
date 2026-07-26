"""Widget de edição baseado em QScintilla (o mesmo motor do Notepad++)."""

import os

from PyQt6.Qsci import (
    QsciScintilla,
    QsciLexerPython, QsciLexerCPP, QsciLexerJavaScript, QsciLexerHTML,
    QsciLexerJSON, QsciLexerBash, QsciLexerJava, QsciLexerSQL,
    QsciLexerMarkdown, QsciLexerXML, QsciLexerYAML, QsciLexerCSS,
    QsciLexerRuby, QsciLexerPerl,
)
from PyQt6.QtGui import QColor, QFont

# Linguagens disponíveis no menu (nome amigável -> classe de lexer)
LANGUAGES = {
    "Texto": None,
    "Bash / Shell": QsciLexerBash,
    "C / C++": QsciLexerCPP,
    "CSS": QsciLexerCSS,
    "HTML": QsciLexerHTML,
    "Java": QsciLexerJava,
    "JavaScript": QsciLexerJavaScript,
    "JSON": QsciLexerJSON,
    "Markdown": QsciLexerMarkdown,
    "Perl": QsciLexerPerl,
    "Python": QsciLexerPython,
    "Ruby": QsciLexerRuby,
    "SQL": QsciLexerSQL,
    "XML": QsciLexerXML,
    "YAML": QsciLexerYAML,
}

# Lookup reverso: classe de lexer -> nome amigável (para detecção por extensão)
_CLASS_TO_NAME = {cls: name for name, cls in LANGUAGES.items() if cls is not None}

# Mapeia extensão de arquivo -> classe de lexer (realce de sintaxe)
LEXER_MAP = {
    ".py": QsciLexerPython, ".pyw": QsciLexerPython,
    ".c": QsciLexerCPP, ".h": QsciLexerCPP, ".cpp": QsciLexerCPP,
    ".cc": QsciLexerCPP, ".hpp": QsciLexerCPP, ".cxx": QsciLexerCPP,
    ".js": QsciLexerJavaScript, ".jsx": QsciLexerJavaScript,
    ".ts": QsciLexerJavaScript, ".mjs": QsciLexerJavaScript,
    ".html": QsciLexerHTML, ".htm": QsciLexerHTML,
    ".json": QsciLexerJSON,
    ".sh": QsciLexerBash, ".bash": QsciLexerBash,
    ".java": QsciLexerJava,
    ".sql": QsciLexerSQL,
    ".md": QsciLexerMarkdown, ".markdown": QsciLexerMarkdown,
    ".xml": QsciLexerXML, ".svg": QsciLexerXML,
    ".yml": QsciLexerYAML, ".yaml": QsciLexerYAML,
    ".css": QsciLexerCSS,
    ".rb": QsciLexerRuby,
    ".pl": QsciLexerPerl, ".pm": QsciLexerPerl,
}

THEMES = {
    "light": {
        "paper": "#ffffff", "text": "#000000",
        "margin_bg": "#f0f0f0", "margin_fg": "#999999",
        "caret_line": "#eef6ff", "selection": "#cfe3ff",
    },
    "dark": {
        "paper": "#1e1e1e", "text": "#dcdcdc",
        "margin_bg": "#252526", "margin_fg": "#858585",
        "caret_line": "#2a2d2e", "selection": "#264f78",
    },
}


class CodeEditor(QsciScintilla):
    """Área de edição com numeração de linha, dobras, auto-indent e temas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None          # caminho no disco (None = novo arquivo)
        self.current_language = "Texto"  # linguagem ativa (para o menu e status)
        self._theme = "dark"
        self._setup()
        self.apply_theme(self._theme)

    # ------------------------------------------------------------------ setup
    def _setup(self):
        font = QFont("Monospace", 11)
        font.setFixedPitch(True)
        self.setFont(font)
        self.setUtf8(True)

        # Margem de números de linha
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginLineNumbers(0, True)

        # Realce da linha atual
        self.setCaretLineVisible(True)

        # Casamento de chaves/parênteses
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)

        # Indentação
        self.setAutoIndent(True)
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setIndentationGuides(True)
        self.setBackspaceUnindents(True)

        # Dobras de código (folding)
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle)

        # Quebra de linha desligada por padrão
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)

        # Ajusta a largura da margem conforme o número de linhas
        self.linesChanged.connect(self._update_margin_width)
        self._update_margin_width()

    def _update_margin_width(self):
        digits = len(str(max(1, self.lines())))
        self.setMarginWidth(0, "0" * (digits + 1))

    # ------------------------------------------------------------------ tema
    def apply_theme(self, name):
        self._theme = name
        t = THEMES[name]
        paper, text = QColor(t["paper"]), QColor(t["text"])

        self.setPaper(paper)
        self.setColor(text)
        self.setCaretLineBackgroundColor(QColor(t["caret_line"]))
        self.setCaretForegroundColor(text)
        self.setMarginsBackgroundColor(QColor(t["margin_bg"]))
        self.setMarginsForegroundColor(QColor(t["margin_fg"]))
        self.setSelectionBackgroundColor(QColor(t["selection"]))
        self.setFoldMarginColors(QColor(t["margin_bg"]), QColor(t["margin_bg"]))

        lexer = self.lexer()
        if lexer is not None:
            self._theme_lexer(lexer)

    def _theme_lexer(self, lexer):
        t = THEMES[self._theme]
        paper, text = QColor(t["paper"]), QColor(t["text"])
        lexer.setDefaultPaper(paper)
        lexer.setDefaultColor(text)
        lexer.setPaper(paper)        # fundo para todos os estilos
        lexer.setColor(text, 0)      # texto normal legível no fundo escuro
        lexer.setFont(self.font())

    # ---------------------------------------------------------------- lexer
    def set_language(self, name):
        """Aplica manualmente o realce de sintaxe de uma linguagem pelo nome."""
        lexer_cls = LANGUAGES.get(name, None)
        self.current_language = name if name in LANGUAGES else "Texto"
        if lexer_cls is None:
            self.setLexer(None)
            self.apply_theme(self._theme)
            return
        lexer = lexer_cls(self)
        lexer.setFont(self.font())
        self.setLexer(lexer)
        self._theme_lexer(lexer)

    def set_lexer_for_path(self, path):
        """Detecta a linguagem automaticamente pela extensão do arquivo."""
        ext = os.path.splitext(path or "")[1].lower()
        lexer_cls = LEXER_MAP.get(ext)
        name = _CLASS_TO_NAME.get(lexer_cls, "Texto")
        self.set_language(name)

    def language_name(self):
        return self.current_language
