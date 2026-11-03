"""Paleta de cores, fontes e logo."""
import base64
import io
import os

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


# Tipografia
# Fontes nomeadas do Tk: os widgets referenciam o nome e configurar_fontes()
# define familia e tamanho uma unica vez. Escala: 7, 8, 9, 10, 11, 13, 15, 20.
FONT    = "AppTexto"        # 10 regular
FONT_B  = "AppTextoForte"   # 10 semibold
FONT_SM = "AppPequena"      # 9 regular
FONT_XS = "AppLegenda"      # 8 regular
F_PEQ_B     = "AppPequenaForte"  # 9 semibold
F_SECAO     = "AppSecao"         # 9 semibold, titulos de secao
F_MINI      = "AppMini"          # 7 semibold, rotulos em maiusculas
F_BOTAO     = "AppBotao"         # 9 medium
F_BOTAO_SM  = "AppBotaoPequeno"  # 8 medium
F_BOTAO_LG  = "AppBotaoGrande"   # 11 semibold
F_BOTAO_XL  = "AppBotaoDestaque" # 15 semibold
F_ABA       = "AppAba"           # 10 semibold
F_SUBTITULO = "AppSubtitulo"     # 11 semibold
F_TITULO    = "AppTitulo"        # 13 semibold
F_MONO      = "AppMono"          # 9 mono
F_MONO_XS   = "AppMonoPequena"   # 8 mono
F_MONO_B    = "AppMonoForte"     # 9 mono semibold
F_MONO_LG   = "AppMonoGrande"    # 12 mono semibold
F_DISPLAY   = "AppDisplay"       # 20 mono semibold, numero em destaque
F_SPLASH    = "AppSplash"        # 20 semibold

_ESCALA = {
    FONT: ("texto", 10), FONT_B: ("semi", 10), FONT_SM: ("texto", 9), FONT_XS: ("texto", 8),
    F_PEQ_B: ("semi", 9), F_SECAO: ("semi", 9), F_MINI: ("semi", 7),
    F_BOTAO: ("medio", 9), F_BOTAO_SM: ("medio", 8), F_BOTAO_LG: ("semi", 11),
    F_BOTAO_XL: ("semi", 15), F_ABA: ("semi", 10), F_SUBTITULO: ("semi", 11),
    F_TITULO: ("semi", 13), F_MONO: ("mono", 9), F_MONO_XS: ("mono", 8),
    F_MONO_B: ("mono_semi", 9), F_MONO_LG: ("mono_semi", 12), F_DISPLAY: ("mono_semi", 20),
    F_SPLASH: ("semi", 20),
}

# Candidatas por papel, em ordem de preferencia. No Windows as variantes
# Medium/SemiBold aparecem como familias proprias (nomes abreviados no arquivo).
_CANDIDATAS = {
    "texto":     ["IBM Plex Sans", "Segoe UI", "DejaVu Sans"],
    "medio":     ["IBM Plex Sans Medm", "IBM Plex Sans Medium"],
    "semi":      ["IBM Plex Sans SmBld", "IBM Plex Sans SemiBold"],
    "mono":      ["IBM Plex Mono", "Consolas", "DejaVu Sans Mono"],
    "mono_semi": ["IBM Plex Mono SmBld", "IBM Plex Mono SemiBold"],
}


def _pasta_fontes():
    from .config import BASE_DIR
    return os.path.join(BASE_DIR, "assets", "fonts")


def registrar_fontes_embutidas():
    """
    Windows: carrega os .ttf de assets/fonts apenas para este processo
    (nada e instalado no sistema). Deve rodar antes de criar a janela Tk.
    """
    if os.name != "nt":
        return 0
    try:
        import ctypes
        gdi32 = ctypes.windll.gdi32
    except Exception:
        return 0
    FR_PRIVATE = 0x10
    total = 0
    pasta = _pasta_fontes()
    try:
        arquivos = [f for f in os.listdir(pasta) if f.lower().endswith((".ttf", ".otf"))]
    except OSError:
        return 0
    for nome in arquivos:
        try:
            total += gdi32.AddFontResourceExW(os.path.join(pasta, nome), FR_PRIVATE, 0)
        except Exception:
            pass
    return total


def configurar_fontes(root):
    """Cria (ou atualiza) as fontes nomeadas com a melhor familia disponivel."""
    import tkinter.font as tkfont
    disponiveis = set(tkfont.families(root))

    def escolher(papel):
        for fam in _CANDIDATAS[papel]:
            if fam in disponiveis:
                return fam, "normal"
        return None

    texto = escolher("texto") or ("TkDefaultFont", "normal")
    mono = escolher("mono") or ("TkFixedFont", "normal")
    papeis = {
        "texto": texto,
        "medio": escolher("medio") or texto,
        "semi": escolher("semi") or (texto[0], "bold"),
        "mono": mono,
        "mono_semi": escolher("mono_semi") or (mono[0], "bold"),
    }
    for nome, (papel, tamanho) in _ESCALA.items():
        familia, peso = papeis[papel]
        f = _fontes_vivas.get(nome)
        if f is None:
            # A referencia precisa ser mantida: o Tk apaga a fonte nomeada
            # quando o objeto Python e coletado.
            f = _fontes_vivas[nome] = tkfont.Font(root=root, name=nome, family=familia,
                                                  size=tamanho, weight=peso)
        else:
            f.configure(family=familia, size=tamanho, weight=peso)
    return papeis


_fontes_vivas = {}


def espacado(texto):
    """Simula espacamento entre letras (tracking) com espacos finos, para rotulos curtos."""
    return "\u2009".join(texto)


def carregar_logo(altura, escuro=None):
    """Logo vetorizada rasterizada em alta resolucao e reduzida para a altura pedida."""
    from PIL import Image, ImageTk
    if escuro is None:
        escuro = _atual == "escuro"
    dados = base64.b64decode(LOGO_B64_ESCURO if escuro else LOGO_B64)
    img = Image.open(io.BytesIO(dados)).convert("RGBA")
    larg = max(1, round(img.width * altura / img.height))
    return ImageTk.PhotoImage(img.resize((larg, altura), Image.LANCZOS))


def aplicar_estilo_ttk(root):
    """Estilo dos widgets ttk (combobox, tabela, barra de rolagem) no tema atual."""
    from tkinter import ttk
    st = ttk.Style(root)
    st.theme_use("clam")
    fundo, campo, borda = T("CARD"), T("ENTRY_BG"), T("BORDER")

    st.configure("TCombobox", fieldbackground=campo, background=fundo,
                 foreground=T("TEXT"), arrowcolor=T("SUBTEXT"), bordercolor=borda,
                 lightcolor=campo, darkcolor=campo, selectbackground=campo,
                 selectforeground=T("TEXT"), padding=(8, 5), arrowsize=13)
    st.map("TCombobox",
           fieldbackground=[("disabled", T("CARD")), ("readonly", campo)],
           foreground=[("disabled", T("MUTED")), ("readonly", T("TEXT"))],
           background=[("disabled", T("CARD")), ("active", T("ACCENT2")), ("readonly", fundo)],
           arrowcolor=[("disabled", T("MUTED"))],
           bordercolor=[("focus", T("ACCENT"))],
           lightcolor=[("focus", campo)], darkcolor=[("focus", campo)],
           selectbackground=[("readonly", campo)],
           selectforeground=[("readonly", T("TEXT"))])
    # Lista suspensa do combobox (widget Tk classico)
    root.option_add("*TCombobox*Listbox.background", T("CARD"))
    root.option_add("*TCombobox*Listbox.foreground", T("TEXT"))
    root.option_add("*TCombobox*Listbox.selectBackground", T("ACCENT"))
    root.option_add("*TCombobox*Listbox.selectForeground", T("TEXT_ON_ACCENT"))
    root.option_add("*TCombobox*Listbox.font", FONT_SM)
    root.option_add("*TCombobox*Listbox.borderWidth", 0)
    root.option_add("*TCombobox*Listbox.relief", "flat")

    st.configure("Treeview", background=T("PANEL"), fieldbackground=T("PANEL"),
                 foreground=T("TEXT"), bordercolor=borda, lightcolor=T("PANEL"),
                 darkcolor=T("PANEL"), rowheight=24, font=FONT_SM)
    st.map("Treeview", background=[("selected", T("ACCENT"))],
           foreground=[("selected", T("TEXT_ON_ACCENT"))])
    st.configure("Treeview.Heading", background=T("CARD"), foreground=T("SUBTEXT"),
                 bordercolor=borda, lightcolor=T("CARD"), darkcolor=T("CARD"),
                 relief="flat", font=F_SECAO, padding=(6, 5))
    st.map("Treeview.Heading", background=[("active", T("ACCENT2"))])

    for orient in ("Vertical", "Horizontal"):
        st.configure(f"{orient}.TScrollbar", background=T("CARD"), troughcolor=T("BG"),
                     bordercolor=T("BG"), lightcolor=T("CARD"), darkcolor=T("CARD"),
                     arrowcolor=T("MUTED"), gripcount=0)
        st.map(f"{orient}.TScrollbar", background=[("active", T("ACCENT2"))])
