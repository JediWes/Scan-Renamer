# Renomeador de Declarações 

Sistema desktop desenvolvido em Python para automatização do fluxo de digitalização e renomeação de documentos em cartório.

## Funcionalidades

- **Renomeador automático** — monitora pastas e renomeia arquivos escaneados no padrão `imageNNNNNN` para declarações de Nascimento, Óbito e Natimorto
- **Scanner integrado** — controle do Brother DS-940DW via WIA (resolução, cor, frente e verso, várias páginas, presets)
- **Digitalizar direto para a declaração** — o PDF é salvo na pasta do tipo escolhido já com o próximo `imageNNNNNN`
- **Papéis maiores que A4** — tamanho de leitura Ofício, Legal ou máximo do scanner, com corte automático da borda que o scanner preenche fora da folha (branca ou preta, nos quatro lados); opção de ajustar ao A4 no PDF (reduz sem cortar, como a impressora)
- **Remoção de versos em branco** — no modo frente e verso, versos vazios são descartados (a frente nunca é removida)
- **Histórico e desfazer** — toda renomeação e digitalização fica registrada em `historico.csv`; a última renomeação pode ser desfeita (Ctrl+Z)
- **Visualizador** — preview de imagens e PDFs com zoom
- **Modo lote** — renomeia arquivos já existentes na pasta
- **Interface animada** — abas e seletor deslizantes, avisos que entram e saem suavemente, botões com transição de cor, status pulsando durante o monitoramento e barra de atividade durante o scan
- **Temas** — modo escuro e claro, com tamanho de janela e aba lembrados
- **Instância única** — abrir o app de novo traz a janela já aberta para frente

## Atalhos

| Tecla | Ação |
|---|---|
| F5 | Iniciar / parar monitoramento |
| F7 | Digitalizar |
| F2 | Verificar numeração da pasta |
| Ctrl+Z | Desfazer última renomeação |
| Ctrl+H | Histórico |
| Ctrl+O | Escolher pasta |
| Ctrl+, | Configurações |
| Ctrl+L | Limpar log |
| F1 | Lista de atalhos |

## Estrutura

```
main.py                  ponto de entrada (instância única)
cartorio/
  constantes.py          versão, tipos de declaração, extensões
  tema.py                cores, fontes, logo e estilo ttk
  config.py              configurações, preferências e presets
  arquivos.py            numeração imageNNNNNN e miniaturas
  scanner.py             WIA via sessão PowerShell, modo de cor, páginas em branco, PDF
  renomeador.py          monitoramento de pasta (watchdog)
  historico.py           registro em CSV e desfazer
  instancia.py           instância única
  logo_data.py           logo embutida
  ui/                    janelas e abas (Tkinter)
    anim.py              motor de animação (curvas, cores, transições)
    widgets.py           botão, abas, seletor, avisos, dicas, barra de atividade
assets/                  logo vetorizada (SVG e PNG) e fontes
```

Arquivos gerados ao lado do `main.py`: `cartorio_config.json`, `scanner_presets.json`, `historico.csv` e `erros.log`.

## Tipografia e abertura

- Fontes **IBM Plex Sans** e **IBM Plex Mono** em `assets/fonts` (licença SIL OFL 1.1, em `assets/fonts/OFL.txt`). São carregadas apenas pelo app, sem instalar nada no Windows; se faltarem, o app usa Segoe UI e Consolas.
- A tela de abertura é desenhada pelo próprio app nas cores da marca. Para usar uma foto como fundo, coloque-a em `assets/splash.jpg` (ou `.png`); ela é recortada para preencher a tela e escurecida para manter o texto legível.

## Logo

`assets/logo.svg` e `assets/logo_escuro.svg` são a logo vetorizada (escalável sem perda). O app embute versões PNG em alta resolução geradas a partir delas.

## Requisitos

- Windows 10/11
- Python 3.11+
- Driver Brother DS-940DW instalado

## Instalação

Execute `instalar_cartorio.bat` para instalar o Python e todas as dependências automaticamente.

Ou instale manualmente:

```bash
pip install Pillow watchdog pypdfium2
```

## Uso

```bash
python main.py
```

## Desenvolvido por

Wesley Lucas Assunção — Análise e Desenvolvimento de Sistemas (UNIP)  
Atividade de extensão universitária — 2025
