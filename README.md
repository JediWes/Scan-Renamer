# Renomeador de Declarações 

Sistema desktop desenvolvido em Python para automatização do fluxo de digitalização e renomeação de documentos em cartório.

## Funcionalidades

- **Renomeador automático** — monitora pastas e renomeia arquivos escaneados no padrão `imageNNNNNN` para declarações de Nascimento, Óbito e Natimorto
- **Scanner integrado** — controle completo do Brother DS-940DW via WIA (resolução, cor, duplex, múltiplas páginas, presets)
- **Visualizador** — preview de imagens e PDFs com zoom
- **Modo lote** — renomeia arquivos já existentes na pasta
- **Temas** — modo escuro e claro, com tamanho de janela e aba lembrados
- **Presets de scanner** — configurações salvas com pasta de destino

## Logo

`assets/logo.svg` é a versão vetorizada da logo (escalável sem perda). O app embute uma versão PNG em alta resolução gerada a partir dela.

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
