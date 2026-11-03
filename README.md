# Renomeador de Declarações 

Sistema desktop desenvolvido em Python para automatização do fluxo de digitalização e renomeação de documentos em cartório.

## Funcionalidades

- **Renomeador automático** — monitora pastas e renomeia arquivos escaneados no padrão `imageNNNNNN` para declarações de Nascimento, Óbito e Natimorto
- **Scanner integrado** — controle do Brother DS-940DW via WIA (resolução, cor, frente e verso, várias páginas, presets)
- **Digitalizar direto para a declaração** — o PDF é salvo na pasta do tipo escolhido já com o próximo `imageNNNNNN`
- **Remoção de versos em branco** — no modo frente e verso, versos vazios são descartados (a frente nunca é removida)
- **Histórico e desfazer** — toda renomeação e digitalização fica registrada em `historico.csv`; a última renomeação pode ser desfeita (Ctrl+Z)
- **Visualizador** — preview de imagens e PDFs com zoom
- **Modo lote** — renomeia arquivos já existentes na pasta
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
assets/                  logo vetorizada (SVG) e PNG
```

Arquivos gerados ao lado do `main.py`: `cartorio_config.json`, `scanner_presets.json`, `historico.csv` e `erros.log`.

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
