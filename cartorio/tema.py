"""Paleta de cores, fontes e logo."""
import base64
import io

from .logo_data import LOGO_B64, LOGO_B64_ESCURO

TEMAS = {
    "escuro": {
        "BG":             "#141617",
        "SIDEBAR":        "#1a1d1f",   # cabecalho / rodape
        "PANEL":          "#1a1d1f",
        "CARD":           "#23272a",
        "CARD2":          "#1e2123",
        "ACCENT":         "#2f9e5f",
        "ACCENT2":        "#2a3035",   # botoes discretos do cabecalho
        "SUCCESS":        "#2f9e5f",
        "DANGER":         "#b3402f",
        "DANGER_HOVER":   "#9a3626",
        "TEXT":           "#e7e9ea",
        "TEXT_ON_ACCENT": "#ffffff",
        "SUBTEXT":        "#a3abb0",
        "MUTED":          "#7a838a",
        "BORDER":         "#2c3236",
        "SEP":            "#2c3236",
        "LOG_BG":         "#101213",
        "LOG_FG":         "#a3abb0",
        "TAB_INATIVO":    "#1a1d1f",
        "TAB_FG_INATIVO": "#7a838a",
        "ENTRY_BG":       "#23272a",
        "HDR_STRIPE":     "#2f9e5f",
        "HDR_FG":         "#c4cacd",
        "NOTIF_BG":       "#17382a",
        "NOTIF_FG":       "#6fd39b",
        "BTN_SEC_BG":     "#2a3035",
        "BTN_SEC_FG":     "#c4cacd",
        "OK":             "#5cc98d",
        "WARN":           "#e3b341",
        "ERR":            "#ef7b6c",
    },
    "claro": {
        "BG":             "#f4f5f4",
        "SIDEBAR":        "#ffffff",
        "PANEL":          "#ffffff",
        "CARD":           "#eceeed",
        "CARD2":          "#f4f5f4",
        "ACCENT":         "#1b7a43",
        "ACCENT2":        "#e6e9e7",
        "SUCCESS":        "#1b7a43",
        "DANGER":         "#b3402f",
        "DANGER_HOVER":   "#9a3626",
        "TEXT":           "#1a1f1c",
        "TEXT_ON_ACCENT": "#ffffff",
        "SUBTEXT":        "#4b5550",
        "MUTED":          "#7b8680",
        "BORDER":         "#dcdfdd",
        "SEP":            "#dcdfdd",
        "LOG_BG":         "#fbfbfb",
        "LOG_FG":         "#3a433e",
        "TAB_INATIVO":    "#ffffff",
        "TAB_FG_INATIVO": "#7b8680",
        "ENTRY_BG":       "#f4f5f4",
        "HDR_STRIPE":     "#1b7a43",
        "HDR_FG":         "#3a433e",
        "NOTIF_BG":       "#dff2e7",
        "NOTIF_FG":       "#14532d",
        "BTN_SEC_BG":     "#e6e9e7",
        "BTN_SEC_FG":     "#2a322d",
        "OK":             "#1b7a43",
        "WARN":           "#9a6700",
        "ERR":            "#b3402f",
    }
}

_atual = "escuro"


def definir_tema(nome):
    global _atual
    _atual = nome if nome in TEMAS else "escuro"


def tema_atual():
    return _atual


def T(k):
    return TEMAS[_atual][k]


FONT    = ("Segoe UI", 10)
FONT_B  = ("Segoe UI", 10, "bold")
FONT_SM = ("Segoe UI", 9)
FONT_XS = ("Segoe UI", 8)


def carregar_logo(altura, escuro=None):
    """Logo vetorizada rasterizada em alta resolucao e reduzida para a altura pedida."""
    from PIL import Image, ImageTk
    if escuro is None:
        escuro = _atual == "escuro"
    dados = base64.b64decode(LOGO_B64_ESCURO if escuro else LOGO_B64)
    img = Image.open(io.BytesIO(dados)).convert("RGBA")
    larg = max(1, round(img.width * altura / img.height))
    return ImageTk.PhotoImage(img.resize((larg, altura), Image.LANCZOS))
