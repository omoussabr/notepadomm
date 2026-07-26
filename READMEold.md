# NotePy

Editor de texto e código para Linux no estilo Notepad++, escrito em Python +
PyQt6 + **QScintilla** (o mesmo motor de edição que o Notepad++ usa).

## Recursos

- Abas múltiplas (fechar, reordenar arrastando)
- Realce de sintaxe para Python, C/C++, JavaScript, HTML, JSON, Markdown,
  YAML, XML, SQL, Java, Bash, Ruby, Perl, CSS (detecção pela extensão)
- Numeração de linhas, dobras de código, guias de indentação, auto-indent
- Localizar e Substituir (com regex, palavra inteira, diferenciar maiúsculas)
- Temas claro e escuro (`Ctrl+Shift+T`)
- Quebra de linha, zoom, casamento de chaves, realce da linha atual
- Aviso de alterações não salvas ao fechar
- Abrir arquivos pela linha de comando: `notepy arquivo.py`

## Estrutura

```
notepy/
├── main.py           # ponto de entrada
├── editor.py         # widget de edição (QScintilla) + temas + lexers
├── main_window.py    # janela, abas, menus, arquivo, localizar/substituir
├── requirements.txt
├── build.sh          # gera binário standalone
├── notepy.desktop    # atalho para o menu de aplicativos
└── assets/notepy.svg # ícone
```

---

## 1. Rodar a partir do código-fonte

No Ubuntu, o QScintilla precisa das libs Qt do sistema:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip libxcb-cursor0

cd notepy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python main.py            # abre o editor
python main.py meu.py     # já abrindo um arquivo
```

> Se aparecer erro `xcb`/plugin de plataforma, o pacote `libxcb-cursor0`
> resolve na maioria dos casos.

---

## 2. Compilar um binário standalone (PyInstaller)

Isso gera um executável que roda **sem precisar de Python instalado** na
máquina do usuário.

```bash
cd notepy
source .venv/bin/activate          # se estiver usando venv
chmod +x build.sh
./build.sh
```

Resultado em `dist/notepy/`. Para rodar:

```bash
./dist/notepy/notepy
```

Para um único arquivo executável (mais lento para iniciar), troque no
`build.sh` o modo por `--onefile`.

---

## 3. Empacotar como AppImage (portátil, roda em qualquer distro)

1. Baixe o `appimagetool`:
   ```bash
   wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
   chmod +x appimagetool-x86_64.AppImage
   sudo mv appimagetool-x86_64.AppImage /usr/local/bin/appimagetool
   ```
2. Descomente o bloco AppImage no final do `build.sh` e rode `./build.sh`.
3. O resultado é `NotePy-x86_64.AppImage` — basta dar `chmod +x` e distribuir.
   O usuário só clica e executa.

---

## 4. Empacotar como `.deb` (instalação no menu do Ubuntu)

```bash
# a partir do binário gerado pelo PyInstaller em dist/notepy/
mkdir -p notepy-deb/DEBIAN
mkdir -p notepy-deb/usr/lib/notepy
mkdir -p notepy-deb/usr/bin
mkdir -p notepy-deb/usr/share/applications
mkdir -p notepy-deb/usr/share/icons/hicolor/scalable/apps

cp -r dist/notepy/* notepy-deb/usr/lib/notepy/
ln -sf /usr/lib/notepy/notepy notepy-deb/usr/bin/notepy
cp notepy.desktop notepy-deb/usr/share/applications/
cp assets/notepy.svg notepy-deb/usr/share/icons/hicolor/scalable/apps/

cat > notepy-deb/DEBIAN/control << 'CTRL'
Package: notepy
Version: 1.0.0
Section: editors
Priority: optional
Architecture: amd64
Maintainer: Omar Moussa <seu-email@exemplo.com>
Description: Editor de texto e codigo estilo Notepad++
CTRL

dpkg-deb --build notepy-deb notepy_1.0.0_amd64.deb
sudo apt install ./notepy_1.0.0_amd64.deb     # instala e aparece no menu
```

---

## 5. Publicar

- **GitHub Releases** (recomendado para o AppImage e o `.deb`): crie um repo,
  faça `git push`, e em *Releases* anexe o `.AppImage`/`.deb`. É o canal mais
  simples para distribuir no Linux.
- **PyPI** (se quiser `pip install notepy`): adicione um `pyproject.toml` com
  um entry-point de console e rode `python -m build` + `twine upload dist/*`.
- **Flathub / Snap Store**: exigem manifesto próprio (Flatpak `.yml` ou
  `snapcraft.yaml`); vale a pena se quiser alcance amplo, mas dá mais trabalho
  de configuração inicial.

Para começar a distribuir rápido, o caminho **AppImage + GitHub Releases** é o
de menor atrito.
