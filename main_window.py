"""Janela principal do NotepadOMM: abas, menus, arquivo e localizar/substituir."""

import os
import json
from xml.dom import minidom
from xml.parsers.expat import ExpatError

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QFileDialog, QMessageBox, QLabel,
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit,
    QPushButton, QCheckBox, QToolBar, QRadioButton,
    QSpinBox, QButtonGroup,
)
from PyQt6.QtGui import (
    QAction, QActionGroup, QKeySequence, QIcon, QPixmap, QPainter,
    QPolygon, QColor,
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QSize
from PyQt6.Qsci import QsciMacro, QsciScintilla

from editor import CodeEditor, LANGUAGES

# Diretório de configuração do usuário (~/.config/notepadomm)
APP_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
    "notepadomm",
)
SESSION_FILE = os.path.join(APP_DIR, "session.json")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
DEFAULT_SETTINGS = {"theme": "dark", "autosave": True, "interval_ms": 30000}


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except OSError:
        pass


def make_icon(kind, size=22):
    """Desenha ícones simples via QPainter (sem depender de tema do sistema)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    if kind == "play":
        p.setBrush(QColor("#3fb950"))
        p.drawPolygon(QPolygon([QPoint(6, 4), QPoint(6, size - 4),
                                QPoint(size - 5, size // 2)]))
    elif kind == "stop":
        p.setBrush(QColor("#f85149"))
        p.drawRect(5, 5, size - 10, size - 10)
    elif kind == "record":
        p.setBrush(QColor("#f85149"))
        p.drawEllipse(5, 5, size - 10, size - 10)
    elif kind == "repeat":
        p.setBrush(QColor("#58a6ff"))
        p.drawPolygon(QPolygon([QPoint(4, 5), QPoint(4, size - 5),
                                QPoint(size // 2, size // 2)]))
        p.drawPolygon(QPolygon([QPoint(size // 2, 5), QPoint(size // 2, size - 5),
                                QPoint(size - 5, size // 2)]))
    p.end()
    return QIcon(pm)


class MacroRunDialog(QDialog):
    """Diálogo estilo Notepad++: repetir N vezes OU até o fim do arquivo."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Executar macro várias vezes")

        self.rb_times = QRadioButton("Repetir")
        self.rb_times.setChecked(True)
        self.spin = QSpinBox()
        self.spin.setRange(1, 1_000_000)
        self.spin.setValue(1)
        self.rb_eof = QRadioButton("Repetir até o fim do arquivo")

        group = QButtonGroup(self)
        group.addButton(self.rb_times)
        group.addButton(self.rb_eof)

        row = QHBoxLayout()
        row.addWidget(self.rb_times)
        row.addWidget(self.spin)
        row.addWidget(QLabel("vez(es)"))
        row.addStretch()

        btns = QHBoxLayout()
        ok = QPushButton("Executar")
        cancel = QPushButton("Cancelar")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(ok)
        btns.addWidget(cancel)

        layout = QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(self.rb_eof)
        layout.addLayout(btns)

    def selection(self):
        """Retorna (times, None) para N vezes ou (None, True) para até o fim."""
        if self.rb_eof.isChecked():
            return None, True
        return self.spin.value(), False

FILE_FILTER = (
    "Todos os arquivos (*);;Python (*.py);;C/C++ (*.c *.cpp *.h *.hpp);;"
    "JavaScript (*.js);;HTML (*.html *.htm);;Markdown (*.md);;"
    "JSON (*.json);;YAML (*.yml *.yaml);;Shell (*.sh)"
)


class FindReplaceDialog(QDialog):
    """Diálogo não-modal de localizar e substituir."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle("Localizar / Substituir")
        self.setModal(False)

        self.find_input = QLineEdit()
        self.replace_input = QLineEdit()
        self.cb_case = QCheckBox("Diferenciar maiúsculas")
        self.cb_word = QCheckBox("Palavra inteira")
        self.cb_regex = QCheckBox("Expressão regular")

        grid = QGridLayout()
        grid.addWidget(QLabel("Localizar:"), 0, 0)
        grid.addWidget(self.find_input, 0, 1)
        grid.addWidget(QLabel("Substituir:"), 1, 0)
        grid.addWidget(self.replace_input, 1, 1)

        opts = QHBoxLayout()
        opts.addWidget(self.cb_case)
        opts.addWidget(self.cb_word)
        opts.addWidget(self.cb_regex)

        btns = QHBoxLayout()
        for label, slot in (
            ("Próxima", self.find_next),
            ("Substituir", self.replace_one),
            ("Substituir tudo", self.replace_all),
            ("Fechar", self.close),
        ):
            b = QPushButton(label)
            b.clicked.connect(slot)
            btns.addWidget(b)

        layout = QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addLayout(opts)
        layout.addLayout(btns)

    def find_next(self):
        editor = self.window.current_editor()
        text = self.find_input.text()
        if not editor or not text:
            return
        found = editor.findFirst(
            text, self.cb_regex.isChecked(), self.cb_case.isChecked(),
            self.cb_word.isChecked(), True, True,
        )
        if not found:
            self.window.status.showMessage("Texto não encontrado", 2000)

    def replace_one(self):
        editor = self.window.current_editor()
        if editor and editor.hasSelectedText():
            editor.replace(self.replace_input.text())
        self.find_next()

    def replace_all(self):
        editor = self.window.current_editor()
        text = self.find_input.text()
        if not editor or not text:
            return
        editor.beginUndoAction()
        count = 0
        if editor.findFirst(
            text, self.cb_regex.isChecked(), self.cb_case.isChecked(),
            self.cb_word.isChecked(), False, True, 0, 0,
        ):
            editor.replace(self.replace_input.text())
            count = 1
            while editor.findNext():
                editor.replace(self.replace_input.text())
                count += 1
        editor.endUndoAction()
        self.window.status.showMessage(f"{count} substituição(ões)", 2000)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NotepadOMM")
        self.resize(1000, 680)
        self.find_dialog = None

        # Configurações persistentes (tema, salvamento automático, intervalo)
        self.settings = {**DEFAULT_SETTINGS, **_load_json(SETTINGS_FILE, {})}
        self.theme = self.settings.get("theme", "dark")
        self.autosave_enabled = bool(self.settings.get("autosave", True))
        self.interval_ms = int(self.settings.get("interval_ms", 30000))

        # Timer que persiste a sessão periodicamente (não grava nos arquivos!)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.save_session)

        # Estado das macros
        self.macro = None          # QsciMacro em gravação
        self.macro_data = None     # última macro gravada (string serializada)
        # Motor de reprodução (baseado em timer, para poder ser interrompido)
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._play_step)
        self.play_obj = None
        self.play_editor = None
        self.play_remaining = None   # int = N vezes; None = até o fim do arquivo
        self.play_last_pos = -1
        self.play_guard = 0

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tabs)

        self.status = self.statusBar()
        self._build_menu()
        self._build_toolbar()
        self.restore_session()
        if self.autosave_enabled:
            self.autosave_timer.start(self.interval_ms)

    # ------------------------------------------------------------- helpers
    def current_editor(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def _tab_title(self, editor):
        name = os.path.basename(editor.file_path) if editor.file_path else "Sem título"
        return ("*" + name) if editor.isModified() else name

    def _connect_editor(self, editor):
        editor.modificationChanged.connect(lambda _=None, e=editor: self._sync_title(e))
        editor.cursorPositionChanged.connect(lambda *_: self._refresh_status())

    def _sync_title(self, editor):
        idx = self.tabs.indexOf(editor)
        if idx != -1:
            self.tabs.setTabText(idx, self._tab_title(editor))

    def _on_tab_changed(self, *_):
        self._refresh_status()
        self._sync_language_menu()

    def _refresh_status(self, *_):
        editor = self.current_editor()
        if not editor:
            self.status.clearMessage()
            return
        line, col = editor.getCursorPosition()
        self.status.showMessage(
            f"Ln {line + 1}, Col {col + 1}    {editor.language_name()}    UTF-8"
        )

    # ---------------------------------------------------------------- menu
    def _act(self, text, slot, shortcut=None):
        a = QAction(text, self)
        a.triggered.connect(slot)
        if shortcut:
            a.setShortcut(shortcut)
        return a

    def _build_menu(self):
        mb = self.menuBar()

        m_file = mb.addMenu("&Arquivo")
        m_file.addAction(self._act("Novo", self.new_tab, QKeySequence.StandardKey.New))
        m_file.addAction(self._act("Abrir…", self.open_dialog, QKeySequence.StandardKey.Open))
        m_file.addAction(self._act("Salvar", self.save, QKeySequence.StandardKey.Save))
        m_file.addAction(self._act("Salvar como…", self.save_as, QKeySequence.StandardKey.SaveAs))
        m_file.addSeparator()
        m_file.addAction(self._act("Fechar aba", self.close_current, QKeySequence.StandardKey.Close))
        m_file.addAction(self._act("Sair", self.close, QKeySequence.StandardKey.Quit))

        m_edit = mb.addMenu("&Editar")
        m_edit.addAction(self._act("Desfazer", lambda: self._ed("undo"), QKeySequence.StandardKey.Undo))
        m_edit.addAction(self._act("Refazer", lambda: self._ed("redo"), QKeySequence.StandardKey.Redo))
        m_edit.addSeparator()
        m_edit.addAction(self._act("Recortar", lambda: self._ed("cut"), QKeySequence.StandardKey.Cut))
        m_edit.addAction(self._act("Copiar", lambda: self._ed("copy"), QKeySequence.StandardKey.Copy))
        m_edit.addAction(self._act("Colar", lambda: self._ed("paste"), QKeySequence.StandardKey.Paste))
        m_edit.addSeparator()
        m_edit.addAction(self._act("Localizar/Substituir…", self.show_find, QKeySequence.StandardKey.Find))

        m_view = mb.addMenu("&Exibir")
        m_view.addAction(self._act("Ampliar", lambda: self._ed("zoomIn"), QKeySequence.StandardKey.ZoomIn))
        m_view.addAction(self._act("Reduzir", lambda: self._ed("zoomOut"), QKeySequence.StandardKey.ZoomOut))
        m_view.addAction(self._act("Quebra de linha", self.toggle_wrap, "Ctrl+Shift+W"))
        m_view.addAction(self._act("Alternar tema", self.toggle_theme, "Ctrl+Shift+T"))

        # --- Linguagem (seleção manual do realce de sintaxe) ---
        m_lang = mb.addMenu("&Linguagem")
        self.lang_group = QActionGroup(self)
        self.lang_group.setExclusive(True)
        self.lang_actions = {}
        for name in LANGUAGES:
            act = QAction(name, self, checkable=True)
            act.triggered.connect(lambda _=False, n=name: self.set_language(n))
            self.lang_group.addAction(act)
            m_lang.addAction(act)
            self.lang_actions[name] = act

        # --- Salvamento automático de sessão ---
        m_auto = mb.addMenu("&Automático")
        self.autosave_action = QAction("Salvamento automático de sessão", self, checkable=True)
        self.autosave_action.setChecked(self.autosave_enabled)
        self.autosave_action.triggered.connect(self.toggle_autosave)
        m_auto.addAction(self.autosave_action)
        m_auto.addSeparator()
        m_auto.addSection("Intervalo")
        self.interval_group = QActionGroup(self)
        self.interval_group.setExclusive(True)
        for label, ms in (("15 segundos", 15000), ("30 segundos", 30000),
                          ("1 minuto", 60000), ("5 minutos", 300000)):
            act = QAction(label, self, checkable=True)
            act.setChecked(ms == self.interval_ms)
            act.triggered.connect(lambda _=False, v=ms: self.set_autosave_interval(v))
            self.interval_group.addAction(act)
            m_auto.addAction(act)

        # --- Macros (gravar / reproduzir, estilo Notepad++) ---
        m_macro = mb.addMenu("&Macro")
        self.record_action = self._act("Iniciar gravação", self.toggle_record, "Ctrl+Shift+R")
        self.record_action.setIcon(make_icon("record"))
        m_macro.addAction(self.record_action)
        self.play_action = self._act("Executar macro (1x)", self.play_macro, "Ctrl+Shift+P")
        self.play_action.setIcon(make_icon("play"))
        self.play_action.setEnabled(False)
        m_macro.addAction(self.play_action)
        self.play_multi_action = self._act("Executar várias vezes…", self.play_macro_multiple)
        self.play_multi_action.setIcon(make_icon("repeat"))
        self.play_multi_action.setEnabled(False)
        m_macro.addAction(self.play_multi_action)
        self.stop_action = self._act("Parar execução", self.stop_play, "Esc")
        self.stop_action.setIcon(make_icon("stop"))
        self.stop_action.setEnabled(False)
        m_macro.addAction(self.stop_action)
        m_macro.addSeparator()
        m_macro.addAction(self._act("Salvar macro…", self.save_macro))
        m_macro.addAction(self._act("Carregar macro…", self.load_macro))

        # --- Ferramentas: pretty print e validação ---
        m_tools = mb.addMenu("&Ferramentas")
        m_tools.addAction(self._act("Formatar documento", self.format_auto, "Ctrl+Alt+L"))
        m_tools.addSeparator()
        m_tools.addAction(self._act("Formatar JSON", self.format_json))
        m_tools.addAction(self._act("Validar JSON", self.validate_json))
        m_tools.addSeparator()
        m_tools.addAction(self._act("Formatar XML", self.format_xml))
        m_tools.addAction(self._act("Validar XML", self.validate_xml))

    def _build_toolbar(self):
        tb = QToolBar("Macros")
        tb.setIconSize(QSize(22, 22))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(tb)
        tb.addAction(self.record_action)
        tb.addAction(self.play_action)        # ícone: executar 1 vez
        tb.addAction(self.play_multi_action)  # ícone: executar N vezes / até o fim
        tb.addAction(self.stop_action)        # ícone: parar execução

    def _ed(self, method):
        editor = self.current_editor()
        if editor:
            getattr(editor, method)()

    # ---------------------------------------------------------------- abas
    def new_tab(self, path=None):
        editor = CodeEditor()
        editor.apply_theme(self.theme)
        self._connect_editor(editor)
        idx = self.tabs.addTab(editor, "Sem título")
        self.tabs.setCurrentIndex(idx)
        editor.setFocus()
        return editor

    def open_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Abrir", "", FILE_FILTER)
        for p in paths:
            self.open_path(p)

    def open_path(self, path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.critical(self, "Erro ao abrir", str(exc))
            return
        editor = self.current_editor()
        # Reaproveita a aba atual se estiver vazia e sem nome
        if not (editor and editor.file_path is None and not editor.text()):
            editor = self.new_tab()
        editor.setText(content)
        editor.file_path = path
        editor.set_lexer_for_path(path)
        editor.apply_theme(self.theme)
        editor.setModified(False)
        self._sync_title(editor)
        self._refresh_status()
        self._sync_language_menu()

    def save(self):
        editor = self.current_editor()
        if not editor:
            return False
        if editor.file_path is None:
            return self.save_as()
        return self._write(editor, editor.file_path)

    def save_as(self):
        editor = self.current_editor()
        if not editor:
            return False
        path, _ = QFileDialog.getSaveFileName(self, "Salvar como", "", FILE_FILTER)
        if not path:
            return False
        if self._write(editor, path):
            editor.file_path = path
            editor.set_lexer_for_path(path)
            editor.apply_theme(self.theme)
            self._sync_title(editor)
            self._refresh_status()
            self._sync_language_menu()
            return True
        return False

    def _write(self, editor, path):
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(editor.text())
        except OSError as exc:
            QMessageBox.critical(self, "Erro ao salvar", str(exc))
            return False
        editor.setModified(False)
        self._sync_title(editor)
        self.status.showMessage(f"Salvo: {path}", 2000)
        return True

    def _maybe_save(self, editor):
        if not editor.isModified():
            return True
        name = os.path.basename(editor.file_path) if editor.file_path else "Sem título"
        resp = QMessageBox.question(
            self, "Alterações não salvas",
            f"Salvar as alterações em “{name}”?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if resp == QMessageBox.StandardButton.Save:
            self.tabs.setCurrentWidget(editor)
            return self.save()
        return resp == QMessageBox.StandardButton.Discard

    def close_current(self):
        self.close_tab(self.tabs.currentIndex())

    def close_tab(self, index):
        editor = self.tabs.widget(index)
        # Com o salvamento automático ligado não perguntamos nada; sem ele,
        # mantemos a proteção contra perder alterações não salvas.
        if isinstance(editor, CodeEditor) and not self.autosave_enabled:
            if not self._maybe_save(editor):
                return
        self.tabs.removeTab(index)
        if self.tabs.count() == 0:
            self.new_tab()
        if self.autosave_enabled:
            self.save_session()

    def closeEvent(self, event):
        self._save_settings()
        if self.autosave_enabled:
            # persiste a sessão silenciosamente e fecha, sem perguntar
            self.save_session()
            event.accept()
            return
        # salvamento automático desligado: protege alterações não salvas
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            if isinstance(editor, CodeEditor) and not self._maybe_save(editor):
                event.ignore()
                return
        event.accept()

    # --------------------------------------------------------------- exibir
    def toggle_wrap(self):
        editor = self.current_editor()
        if not editor:
            return
        from PyQt6.Qsci import QsciScintilla
        current = editor.wrapMode()
        editor.setWrapMode(
            QsciScintilla.WrapMode.WrapNone
            if current != QsciScintilla.WrapMode.WrapNone
            else QsciScintilla.WrapMode.WrapWord
        )

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            if isinstance(editor, CodeEditor):
                editor.apply_theme(self.theme)
        self._save_settings()

    def show_find(self):
        if self.find_dialog is None:
            self.find_dialog = FindReplaceDialog(self)
        editor = self.current_editor()
        if editor and editor.hasSelectedText():
            self.find_dialog.find_input.setText(editor.selectedText())
        self.find_dialog.show()
        self.find_dialog.raise_()
        self.find_dialog.find_input.setFocus()

    # ------------------------------------------------------------ linguagem
    def set_language(self, name):
        editor = self.current_editor()
        if editor:
            editor.set_language(name)
            self._refresh_status()
        self._sync_language_menu()

    def _sync_language_menu(self):
        editor = self.current_editor()
        name = editor.current_language if editor else "Texto"
        act = self.lang_actions.get(name)
        if act:
            act.setChecked(True)

    # ------------------------------------ salvamento automático de sessão
    def _save_settings(self):
        self.settings.update({
            "theme": self.theme,
            "autosave": self.autosave_enabled,
            "interval_ms": self.interval_ms,
        })
        _save_json(SETTINGS_FILE, self.settings)

    def toggle_autosave(self, checked):
        self.autosave_enabled = bool(checked)
        if self.autosave_enabled:
            self.autosave_timer.start(self.interval_ms)
            self.save_session()
            self.status.showMessage("Salvamento automático de sessão ligado", 2000)
        else:
            self.autosave_timer.stop()
            self.status.showMessage("Salvamento automático de sessão desligado", 2000)
        self._save_settings()

    def set_autosave_interval(self, ms):
        self.interval_ms = ms
        if self.autosave_timer.isActive():
            self.autosave_timer.start(ms)  # reinicia com o novo intervalo
        self._save_settings()

    def _tab_state(self, editor):
        line, col = editor.getCursorPosition()
        state = {
            "path": editor.file_path,
            "language": editor.current_language,
            "cursor": [line, col],
            "modified": editor.isModified(),
        }
        # Guarda o conteúdo se houver alterações não salvas ou se for aba sem
        # arquivo. Abas salvas em disco são recarregadas do próprio arquivo.
        if editor.isModified() or not editor.file_path:
            state["text"] = editor.text()
        return state

    def save_session(self):
        tabs = []
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            if not isinstance(editor, CodeEditor):
                continue
            # ignora aba totalmente vazia e sem nome
            if editor.file_path is None and not editor.text():
                continue
            tabs.append(self._tab_state(editor))
        _save_json(SESSION_FILE, {"tabs": tabs, "current": self.tabs.currentIndex()})

    def restore_session(self):
        data = _load_json(SESSION_FILE, {})
        restored = 0
        for state in data.get("tabs", []):
            if self._restore_tab(state):
                restored += 1
        if restored == 0:
            self.new_tab()          # primeira execução: aba em branco
        else:
            idx = data.get("current", 0)
            if 0 <= idx < self.tabs.count():
                self.tabs.setCurrentIndex(idx)
        self._on_tab_changed()

    def _restore_tab(self, state):
        path = state.get("path")
        text = state.get("text")
        if text is None:
            # sem texto guardado: recarrega do disco (aba estava salva)
            if not path or not os.path.exists(path):
                return False
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    text = fh.read()
            except (OSError, UnicodeDecodeError):
                return False
            modified = False
        else:
            modified = bool(state.get("modified", False))

        editor = self.new_tab()
        editor.setText(text)
        editor.file_path = path
        lang = state.get("language")
        if lang and lang != "Texto":
            editor.set_language(lang)
        else:
            editor.set_lexer_for_path(path or "")
        editor.apply_theme(self.theme)
        cur = state.get("cursor") or [0, 0]
        editor.setCursorPosition(max(0, cur[0]), max(0, cur[1]))
        editor.setModified(modified)
        self._sync_title(editor)
        return True

    # ---------------------------------------------------------------- macros
    def toggle_record(self):
        editor = self.current_editor()
        if not editor:
            return
        if self.macro is None:
            # começa a gravar as ações de edição na aba atual
            self.macro = QsciMacro(editor)
            self.macro.startRecording()
            self.record_action.setText("Parar gravação")
            self.status.showMessage("Gravando macro…", 0)
        else:
            self.macro.endRecording()
            self.macro_data = self.macro.save()
            self.macro = None
            self.record_action.setText("Iniciar gravação")
            self.status.showMessage("Macro gravada", 2000)
            self._set_playing(False)   # habilita os botões de reprodução

    def _set_playing(self, playing):
        """Atualiza o estado dos botões conforme uma execução em andamento."""
        has_macro = bool(self.macro_data)
        self.stop_action.setEnabled(playing)
        self.play_action.setEnabled(not playing and has_macro)
        self.play_multi_action.setEnabled(not playing and has_macro)
        self.record_action.setEnabled(not playing)

    def _start_playback(self, times, until_eof):
        if not self.macro_data:
            QMessageBox.information(self, "Macro", "Nenhuma macro gravada ainda.")
            return
        editor = self.current_editor()
        if not editor:
            return
        self.play_editor = editor
        self.play_obj = QsciMacro(editor)
        self.play_obj.load(self.macro_data)
        self.play_remaining = None if until_eof else times
        self.play_last_pos = -1
        self.play_guard = 0
        editor.beginUndoAction()       # toda a execução vira um único "desfazer"
        self._set_playing(True)
        self.play_timer.start(0)       # um passo por ciclo do event loop

    def _play_step(self):
        editor = self.play_editor
        if editor is None:
            self.play_timer.stop()
            return
        # Modo "até o fim do arquivo": para ao chegar no fim ou se não avançar
        if self.play_remaining is None:
            pos = editor.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
            length = editor.SendScintilla(QsciScintilla.SCI_GETLENGTH)
            if pos >= length or pos == self.play_last_pos or self.play_guard > 2_000_000:
                self._finish_playback()
                return
            self.play_last_pos = pos
        self.play_obj.play()
        self.play_guard += 1
        # Modo "N vezes": decrementa e encerra ao zerar
        if self.play_remaining is not None:
            self.play_remaining -= 1
            if self.play_remaining <= 0:
                self._finish_playback()

    def _finish_playback(self, interrupted=False):
        self.play_timer.stop()
        if self.play_editor is not None:
            self.play_editor.endUndoAction()
        self.play_editor = None
        self.play_obj = None
        self._set_playing(False)
        self.status.showMessage(
            "Execução interrompida" if interrupted else "Macro executada", 2000
        )

    def stop_play(self):
        if self.play_editor is not None:
            self._finish_playback(interrupted=True)

    def play_macro(self):
        self._start_playback(1, until_eof=False)

    def play_macro_multiple(self):
        dlg = MacroRunDialog(self)
        if dlg.exec():
            times, until_eof = dlg.selection()
            self._start_playback(times, until_eof)

    def save_macro(self):
        if not self.macro_data:
            QMessageBox.information(self, "Macro", "Nenhuma macro gravada ainda.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar macro", "", "Macro NotepadOMM (*.macro);;Todos (*)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.macro_data)
            self.status.showMessage(f"Macro salva: {path}", 2000)

    def load_macro(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Carregar macro", "", "Macro NotepadOMM (*.macro);;Todos (*)"
        )
        if not path:
            return
        with open(path, "r", encoding="utf-8") as fh:
            self.macro_data = fh.read()
        self._set_playing(False)
        self.status.showMessage("Macro carregada", 2000)

    # ---------------------------------------------------- ferramentas (fmt)
    def _replace_all_text(self, editor, new_text):
        """Substitui todo o conteúdo preservando o histórico de desfazer."""
        editor.beginUndoAction()
        editor.selectAll()
        editor.replaceSelectedText(new_text)
        editor.endUndoAction()

    def _goto(self, editor, line1, col1):
        """Posiciona o cursor a partir de linha/coluna 1-based (com clamp)."""
        line = max(0, (line1 or 1) - 1)
        col = max(0, (col1 or 1) - 1)
        editor.setCursorPosition(line, col)
        editor.ensureLineVisible(line)
        editor.setFocus()

    def format_auto(self):
        """Formata conforme a linguagem ativa da aba (JSON ou XML)."""
        editor = self.current_editor()
        if not editor:
            return
        lang = editor.current_language
        if lang == "JSON":
            self.format_json()
        elif lang in ("XML", "HTML"):
            self.format_xml()
        else:
            self.status.showMessage(
                "Formatação automática: selecione JSON ou XML no menu Linguagem", 3000
            )

    # ----- JSON -----
    def format_json(self):
        editor = self.current_editor()
        if not editor:
            return
        text = editor.text()
        if not text.strip():
            self.status.showMessage("Documento vazio", 2000)
            return
        try:
            obj = json.loads(text)
        except json.JSONDecodeError as exc:
            self._goto(editor, exc.lineno, exc.colno)
            QMessageBox.warning(
                self, "JSON inválido",
                f"Erro na linha {exc.lineno}, coluna {exc.colno}:\n{exc.msg}",
            )
            return
        pretty = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False)
        self._replace_all_text(editor, pretty)
        self.status.showMessage("JSON formatado", 2000)

    def validate_json(self):
        editor = self.current_editor()
        if not editor:
            return
        text = editor.text()
        if not text.strip():
            self.status.showMessage("Documento vazio", 2000)
            return
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            self._goto(editor, exc.lineno, exc.colno)
            QMessageBox.critical(
                self, "JSON inválido",
                f"Linha {exc.lineno}, coluna {exc.colno}:\n{exc.msg}",
            )
            return
        QMessageBox.information(self, "JSON válido", "O JSON está bem formado. ✓")

    # ----- XML -----
    def _pretty_xml(self, text):
        """Formata e retorna o XML, ou levanta ExpatError se inválido."""
        dom = minidom.parseString(text.encode("utf-8"))
        pretty = dom.toprettyxml(indent="  ", encoding=None)
        # remove linhas em branco que o minidom costuma inserir
        lines = [ln for ln in pretty.splitlines() if ln.strip()]
        return "\n".join(lines)

    def format_xml(self):
        editor = self.current_editor()
        if not editor:
            return
        text = editor.text()
        if not text.strip():
            self.status.showMessage("Documento vazio", 2000)
            return
        try:
            pretty = self._pretty_xml(text)
        except ExpatError as exc:
            self._goto(editor, exc.lineno, exc.offset + 1)
            QMessageBox.warning(
                self, "XML inválido",
                f"Erro na linha {exc.lineno}, coluna {exc.offset + 1}:\n{exc}",
            )
            return
        self._replace_all_text(editor, pretty)
        self.status.showMessage("XML formatado", 2000)

    def validate_xml(self):
        editor = self.current_editor()
        if not editor:
            return
        text = editor.text()
        if not text.strip():
            self.status.showMessage("Documento vazio", 2000)
            return
        try:
            minidom.parseString(text.encode("utf-8"))
        except ExpatError as exc:
            self._goto(editor, exc.lineno, exc.offset + 1)
            QMessageBox.critical(
                self, "XML inválido",
                f"Linha {exc.lineno}, coluna {exc.offset + 1}:\n{exc}",
            )
            return
        QMessageBox.information(self, "XML válido", "O XML está bem formado. ✓")
