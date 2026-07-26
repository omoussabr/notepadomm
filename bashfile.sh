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
  --name notepy \
  --windowed \
  --add-data "assets/notepy.svg:assets" \
  main.py

echo ""
echo ">> Binário gerado em: dist/notepy/notepy"
echo ">> Para rodar:  ./dist/notepy/notepy"

# ---- AppImage (opcional) ------------------------------------------------
# Requer 'appimagetool'. Descomente para gerar um .AppImage portátil.
#
# APPDIR=NotePy.AppDir
# rm -rf "$APPDIR" && mkdir -p "$APPDIR/usr/bin"
# cp -r dist/notepy/* "$APPDIR/usr/bin/"
# cp assets/notepy.svg "$APPDIR/notepy.svg"
# cp notepy.desktop "$APPDIR/notepy.desktop"
# cat > "$APPDIR/AppRun" << 'RUN'
# #!/bin/bash
# HERE="$(dirname "$(readlink -f "$0")")"
# exec "$HERE/usr/bin/notepy" "$@"
# RUN
# chmod +x "$APPDIR/AppRun"
# appimagetool "$APPDIR" NotePy-x86_64.AppImage
