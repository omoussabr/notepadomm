# NotepadOMM

Editor de texto e código para Linux no estilo Notepad++, escrito em Python +
PyQt6 + **QScintilla** (o mesmo motor de edição que o Notepad++ usa).

## Recursos

- Abas múltiplas (fechar, reordenar arrastando)
- Realce de sintaxe para Python, C/C++, JavaScript, HTML, JSON, Markdown,
  YAML, XML, SQL, Java, Bash, Ruby, Perl, CSS (detecção pela extensão)
- Numeração de linhas, dobras de código, guias de indentação, auto-indent
- **Seleção manual de linguagem** pelo menu *Linguagem* (força o realce mesmo
  sem extensão reconhecida; a barra de status mostra a linguagem ativa)
- **Salvamento automático de sessão** (menu *Automático*, ligado por padrão):
  guarda o estado de todas as abas — inclusive as sem nome e as não salvas — em
  segundo plano, com intervalo configurável (15 s, 30 s, 1 min, 5 min). Ao
  fechar e reabrir, o app volta com todas as abas como estavam, sem perguntar
  se quer salvar. Ele **nunca grava nos seus arquivos** — isso só acontece
  quando você manda salvar (`Ctrl+S`)
- **Configurações lembradas** entre execuções: tema, salvamento automático e
  intervalo ficam salvos em `~/.config/notepadomm/`
- **Macros estilo Notepad++** (menu *Macro* + barra de ferramentas com ícones):
  gravar/parar (`Ctrl+Shift+R`), executar 1x (`Ctrl+Shift+P`), executar N vezes
  **ou até o fim do arquivo**, parar a execução (`Esc`) e salvar/carregar macro
- **Ferramentas** (menu *Ferramentas*): *pretty print* e validação de **JSON**
  e **XML** — formatar (`Ctrl+Alt+L` formata conforme a linguagem da aba) e
  validar, com o cursor pulando direto para a linha/coluna do erro
- Localizar e Substituir (com regex, palavra inteira, diferenciar maiúsculas)
- Temas claro e escuro (`Ctrl+Shift+T`)
- Quebra de linha, zoom, casamento de chaves, realce da linha atual
- Aviso de alterações não salvas ao fechar
- Abrir arquivos pela linha de comando: `notepadomm arquivo.py`

## Estrutura

```
notepadomm/
├── main.py           # ponto de entrada
├── editor.py         # widget de edição (QScintilla) + temas + lexers
├── main_window.py    # janela, abas, menus, arquivo, localizar/substituir
├── requirements.txt
├── build.sh          # gera binário standalone
├── notepadomm.desktop    # atalho para o menu de aplicativos
└── assets/notepadomm.svg # ícone
```

## Usando os recursos novos

- **Linguagem manual:** menu *Linguagem* → escolha uma. Útil para arquivos sem
  extensão ou com extensão incomum. A opção marcada acompanha a aba atual.
- **Salvamento automático de sessão:** menu *Automático* (ligado por padrão).
  O app guarda periodicamente o estado de todas as abas e, ao ser fechado,
  reabre exatamente como estava — sem diálogo de "salvar?". Esse mecanismo
  grava apenas em `~/.config/notepadomm/session.json`, nunca nos seus arquivos;
  para gravar no arquivo de verdade, use *Salvar* (`Ctrl+S`). Se você
  desligar o salvamento automático, o app volta a perguntar sobre alterações
  não salvas ao fechar.
- **Macros:** posicione o cursor, *Macro → Iniciar gravação* (`Ctrl+Shift+R`),
  faça a sequência de edição, *Parar gravação*. Depois use a barra de
  ferramentas: ▶ (verde) executa **1 vez**, ⏩ (azul) abre o diálogo para
  repetir **N vezes** ou **até o fim do arquivo**, e ⏹ (vermelho) **para** a
  execução a qualquer momento — útil para interromper um "até o fim" longo. A
  macro pode ser reproduzida em qualquer aba e salva em `.macro` para reutilizar.
  Dica: o modo "até o fim do arquivo" é feito para macros que **avançam** o
  cursor (ex.: descer linha + editar); ele para sozinho quando chega ao fim.
- **Formatar/validar JSON e XML:** menu *Ferramentas*. *Formatar documento*
  (`Ctrl+Alt+L`) reindenta conforme a linguagem ativa da aba; há também os itens
  específicos *Formatar/Validar JSON* e *Formatar/Validar XML*. Se houver erro,
  aparece a mensagem com linha e coluna e o cursor salta para o ponto do
  problema. Se estiver tudo certo, uma caixa confirma que está bem formado.

---

## 1. Rodar a partir do código-fonte

No Ubuntu, o QScintilla precisa das libs Qt do sistema:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip libxcb-cursor0

cd notepadomm
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
cd notepadomm
source .venv/bin/activate          # se estiver usando venv
chmod +x build.sh
./build.sh
```

Resultado em `dist/notepadomm/`. Para rodar:

```bash
./dist/notepadomm/notepadomm
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
3. O resultado é `NotepadOMM-x86_64.AppImage` — basta dar `chmod +x` e distribuir.
   O usuário só clica e executa.

---

## 4. Empacotar como `.deb` (instalação no menu do Ubuntu)

```bash
# a partir do binário gerado pelo PyInstaller em dist/notepadomm/
mkdir -p notepadomm-deb/DEBIAN
mkdir -p notepadomm-deb/usr/lib/notepadomm
mkdir -p notepadomm-deb/usr/bin
mkdir -p notepadomm-deb/usr/share/applications
mkdir -p notepadomm-deb/usr/share/icons/hicolor/scalable/apps

cp -r dist/notepadomm/* notepadomm-deb/usr/lib/notepadomm/
ln -sf /usr/lib/notepadomm/notepadomm notepadomm-deb/usr/bin/notepadomm
cp notepadomm.desktop notepadomm-deb/usr/share/applications/
cp assets/notepadomm.svg notepadomm-deb/usr/share/icons/hicolor/scalable/apps/

cat > notepadomm-deb/DEBIAN/control << 'CTRL'
Package: notepadomm
Version: 1.0.0
Section: editors
Priority: optional
Architecture: amd64
Maintainer: Omar Moussa <seu-email@exemplo.com>
Description: Editor de texto e codigo estilo Notepad++
CTRL

dpkg-deb --build notepadomm-deb notepadomm_1.0.0_amd64.deb
sudo apt install ./notepadomm_1.0.0_amd64.deb     # instala e aparece no menu
```

---

## 5. Publicar

- **GitHub Releases** (recomendado para o AppImage e o `.deb`): crie um repo,
  faça `git push`, e em *Releases* anexe o `.AppImage`/`.deb`. É o canal mais
  simples para distribuir no Linux.
- **PyPI** (se quiser `pip install notepadomm`): adicione um `pyproject.toml` com
  um entry-point de console e rode `python -m build` + `twine upload dist/*`.
- **Flathub / Snap Store**: exigem manifesto próprio (Flatpak `.yml` ou
  `snapcraft.yaml`); vale a pena se quiser alcance amplo, mas dá mais trabalho
  de configuração inicial.

Para começar a distribuir rápido, o caminho **AppImage + GitHub Releases** é o
de menor atrito.
