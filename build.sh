#!/usr/bin/env bash
# Gera um binário standalone (e, opcionalmente, um AppImage).
# NÃO rode com sudo. Rode como seu usuário normal: ./build.sh
set -e
cd "$(dirname "$0")"

VENV=".venv"

# Cria o ambiente virtual na primeira vez (evita o erro PEP 668 do Ubuntu 24)
if [ ! -d "$VENV" ]; then
  echo ">> Criando ambiente virtual em $VENV..."
  python3 -m venv "$VENV"
fi

PIP="$VENV/bin/pip"
PYINSTALLER="$VENV/bin/pyinstaller"

echo ">> Instalando dependências de build no venv..."
"$PIP" install --upgrade pip
"$PIP" install pyinstaller PyQt6 PyQt6-QScintilla

echo ">> Compilando binário com PyInstaller..."
"$PYINSTALLER" --noconfirm --clean \
  --name notepadomm \
  --windowed \
  --add-data "assets/notepadomm.svg:assets" \
  main.py

echo ""
echo ">> Binário gerado em: dist/notepadomm/notepadomm"
echo ">> Para rodar:  ./dist/notepadomm/notepadomm"

# ---- AppImage (opcional) ------------------------------------------------
# Requer 'appimagetool'. Descomente para gerar um .AppImage portátil.
#
# APPDIR=NotepadOMM.AppDir
# rm -rf "$APPDIR" && mkdir -p "$APPDIR/usr/bin"
# cp -r dist/notepadomm/* "$APPDIR/usr/bin/"
# cp assets/notepadomm.svg "$APPDIR/notepadomm.svg"
# cp notepadomm.desktop "$APPDIR/notepadomm.desktop"
# cat > "$APPDIR/AppRun" << 'RUN'
# #!/bin/bash
# HERE="$(dirname "$(readlink -f "$0")")"
# exec "$HERE/usr/bin/notepadomm" "$@"
# RUN
# chmod +x "$APPDIR/AppRun"
# appimagetool "$APPDIR" NotepadOMM-x86_64.AppImage
