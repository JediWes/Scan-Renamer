"""
Tela de abertura: arte gerada nas cores da marca e uma pequena animacao que
conta o que o app faz (folhas chegam, o scanner passa, o arquivo ganha nome).
Se existir assets/splash.jpg (ou .png), a imagem e usada como fundo.
"""
import os
import tkinter as tk

from ..config import BASE_DIR
from ..constantes import VERSAO
from ..tema import FONT_SM, FONT_XS, F_SPLASH, carregar_logo
from . import anim

LARGURA, ALTURA = 680, 400
DURACAO_MS = 2300
MENSAGENS = ["Carregando configurações…", "Preparando monitoramento…",
             "Conectando ao scanner…", "Pronto"]

# Paleta fixa da abertura (independe do tema)
FUNDO = "#0b1510"
BRANCO = "#f2f5f3"
SUAVE = "#9fb3a8"
APAGADO = "#5d7366"
VERDE = "#2f9e5f"
VERDE_CLARO = "#7fd8a4"

_ASSETS = os.path.join(BASE_DIR, "assets")


def _rgb(h, a=255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def _fonte_pil(nome, tamanho):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(os.path.join(_ASSETS, "fonts", nome), tamanho)
    except OSError:
        return ImageFont.load_default()


def gerar_fundo(w, h):
    """Fundo: brilhos difusos (malha de gradiente), arcos finos e granulado."""
    from PIL import Image, ImageDraw, ImageFilter, ImageOps

    foto = None
    for nome in ("splash.jpg", "splash.jpeg", "splash.png"):
        caminho = os.path.join(_ASSETS, nome)
        if os.path.exists(caminho):
            try:
                foto = ImageOps.fit(Image.open(caminho).convert("RGB"), (w, h), Image.LANCZOS)
            except OSError:
                foto = None
            break

    if foto is not None:
        base = Image.blend(foto, Image.new("RGB", (w, h), FUNDO), 0.35).convert("RGBA")
    else:
        base = Image.new("RGBA", (w, h), _rgb(FUNDO))
        brilhos = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(brilhos)
        for cx, cy, r, cor, a in ((0.80, 0.38, 190, VERDE, 210), (1.02, 0.92, 170, "#0f6b4a", 230),
                                  (0.56, 1.05, 180, "#174f33", 220), (0.70, 0.02, 120, VERDE_CLARO, 120),
                                  (1.05, 0.25, 140, "#1f8a7a", 160), (0.30, 0.15, 160, "#10261a", 255)):
            x, y = cx * w, cy * h
            d.ellipse((x - r, y - r, x + r, y + r), fill=_rgb(cor, a))
        base = Image.alpha_composite(base, brilhos.filter(ImageFilter.GaussianBlur(70)))

    # Arcos concentricos finos a partir do canto inferior direito
    arcos = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(arcos)
    cx, cy = w * 0.98, h * 1.1
    for i, r in enumerate(range(90, 900, 24)):
        a = max(0, 26 - i)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, a), width=1)
    base = Image.alpha_composite(base, arcos)

    # Escurece a esquerda para o texto ler bem
    grad = Image.linear_gradient("L").rotate(90).resize((w, h))
    grad = grad.point(lambda v: int(max(0, v - 70) * 0.85))
    sombra = Image.new("RGBA", (w, h), _rgb(FUNDO))
    sombra.putalpha(grad)
    base = Image.alpha_composite(base, sombra)

    # Granulado leve
    ruido = Image.effect_noise((w, h), 40).convert("RGBA")
    base = Image.blend(base, ruido, 0.035)
    return base.convert("RGB")


def gerar_folha(w=148, h=192, angulo=0, destaque=False):
    """Folha de documento com sombra, linhas de texto e carimbo."""
    from PIL import Image, ImageDraw, ImageFilter
    m = 24
    img = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle((m + 4, m + 10, m + w + 4, m + h + 10), 8,
                                             fill=(0, 0, 0, 120))
    img = Image.alpha_composite(img, sombra.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((m, m, m + w, m + h), 7, fill=_rgb("#f4f6f5" if destaque else "#dfe5e1"))
    x0 = m + 16
    d.rounded_rectangle((x0, m + 18, x0 + 70, m + 26), 3, fill=_rgb("#3c4a42"))
    linhas = [0.86, 0.92, 0.64, 0.88, 0.78, 0.9, 0.52, 0.84, 0.7]
    for i, f in enumerate(linhas):
        y = m + 44 + i * 13
        d.rounded_rectangle((x0, y, x0 + (w - 32) * f, y + 4), 2, fill=_rgb("#9aa79f"))
    d.ellipse((m + w - 52, m + h - 54, m + w - 18, m + h - 20), outline=_rgb(VERDE), width=3)
    d.line((m + 18, m + h - 28, m + 70, m + h - 34), fill=_rgb("#33415f"), width=2)
    if angulo:
        img = img.rotate(angulo, resample=Image.BICUBIC, expand=True)
    return img


def gerar_feixe(w):
    """Faixa de luz do scanner: brilho vertical suave com nucleo claro."""
    from PIL import Image, ImageDraw
    h = 44
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = 1 - abs(y - h / 2) / (h / 2)
        d.line((0, y, w, y), fill=_rgb("#5cf0a0", int(150 * t ** 2.2)))
    d.line((0, h // 2, w, h // 2), fill=(235, 255, 244, 240), width=2)
    # Pontas esmaecidas
    mascara = Image.new("L", (w, h), 255)
    md = ImageDraw.Draw(mascara)
    for x in range(18):
        md.line((x, 0, x, h), fill=int(255 * x / 18))
        md.line((w - 1 - x, 0, w - 1 - x, h), fill=int(255 * x / 18))
    alfa = Image.composite(img.getchannel("A"), Image.new("L", (w, h), 0), mascara)
    img.putalpha(alfa)
    return img


def gerar_selo(texto):
    """Pilula com marca de confirmacao e o nome do arquivo."""
    from PIL import Image, ImageDraw
    f = _fonte_pil("IBMPlexMono-SemiBold.ttf", 15)
    s = 2
    fb = _fonte_pil("IBMPlexMono-SemiBold.ttf", 15 * s)
    tw = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(texto, font=f))
    w, h = tw + 58, 34
    img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w * s - 1, h * s - 1), h * s // 2, fill=_rgb("#1b7a43"))
    d.ellipse((7 * s, 7 * s, 27 * s, 27 * s), fill=_rgb(VERDE_CLARO))
    d.line(((12 * s, 17 * s), (16 * s, 21 * s), (23 * s, 13 * s)), fill=_rgb("#0b3d22"),
           width=3 * s, joint="curve")
    d.text((36 * s, h * s / 2), texto, font=fb, fill=_rgb(BRANCO), anchor="lm")
    return img.resize((w, h), Image.LANCZOS)


class SplashScreen(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(bg=FUNDO)
        self.attributes("-topmost", True)
        W, H = LARGURA, ALTURA
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")
        self._ok = True
        self.cv = tk.Canvas(self, width=W, height=H, bg=FUNDO, highlightthickness=0, bd=0)
        self.cv.pack(fill="both", expand=True)
        self._imgs = {}
        try:
            self._montar_cena(W, H)
        except Exception:
            # Sem Pillow ou falha de desenho: abertura simples
            self.cv.create_text(36, H / 2, text="Renomeador de Declarações", anchor="w",
                                font=F_SPLASH, fill=BRANCO)
            self._folhas, self._feixe, self._selo = [], None, None
        anim.surgir(self, 240)
        self.update()
        self._animar()

    # cena

    def _foto(self, chave, img):
        from PIL import ImageTk
        self._imgs[chave] = ImageTk.PhotoImage(img, master=self)
        return self._imgs[chave]

    def _montar_cena(self, W, H):
        cv = self.cv
        cv.create_image(0, 0, anchor="nw", image=self._foto("fundo", gerar_fundo(W, H)))

        # Folhas (de tras para frente): posicao final e angulo
        cx, cy = W * 0.74, H * 0.47
        especificacao = [(cx + 34, cy - 10, 9, False), (cx - 30, cy + 6, -7, False),
                         (cx, cy, 2, True)]
        self._folhas = []
        for i, (x, y, ang, dest) in enumerate(especificacao):
            img = gerar_folha(angulo=ang, destaque=dest)
            item = cv.create_image(x, H + img.height / 2 + 20, image=self._foto(f"f{i}", img))
            self._folhas.append((item, x, y))
        self._area_scan = (cx - 74, cy - 96, cx + 74, cy + 96)

        self._feixe = cv.create_image(-500, -500, image=self._foto("feixe", gerar_feixe(190)))
        selo = gerar_selo("image000121.pdf")
        self._selo_pos = (cx - 46, cy + 104)
        self._selo = cv.create_image(-600, self._selo_pos[1], image=self._foto("selo", selo))

        # Textos
        try:
            self._logo_img = carregar_logo(58, escuro=True)
            self._logo = cv.create_image(36, 34, anchor="nw", image=self._logo_img)
        except Exception:
            self._logo = None
        self._titulo = cv.create_text(36, 196, anchor="w", text="Renomeador de\nDeclarações",
                                      font=F_SPLASH, fill=FUNDO, justify="left")
        self._sub = cv.create_text(36, 254, anchor="w", font=FONT_SM, fill=FUNDO,
                                   text="Cartório Santa Cruz  ·  2º Subdistrito")
        self._msg = cv.create_text(36, H - 30, anchor="w", font=FONT_XS, fill=APAGADO,
                                   text=MENSAGENS[0])
        cv.create_text(W - 24, H - 30, anchor="e", font=FONT_XS, fill=APAGADO,
                       text=f"Versão {VERSAO}  ·  Wesley Lucas Assunção")
        cv.create_rectangle(0, H - 3, W, H, fill="#14261c", width=0)
        self._barra = cv.create_rectangle(0, H - 3, 0, H, fill=VERDE, width=0)

    # animacao

    def _subir_texto(self, item, y_final, cor, atraso, dur=520):
        cv = self.cv

        def iniciar():
            if not self._ok:
                return

            def quadro(p):
                x = cv.coords(item)[0]
                cv.coords(item, x, y_final + 16 * (1 - p))
                cv.itemconfigure(item, fill=anim.misturar(FUNDO, cor, p))
            anim.animar(cv, ("texto", item), dur, quadro)
        self.after(atraso, iniciar)

    def _animar(self):
        cv = self.cv
        # Folhas chegam de baixo, uma depois da outra
        for i, (item, x, y) in enumerate(getattr(self, "_folhas", [])):
            def chegar(item=item, x=x, y=y):
                if not self._ok:
                    return
                y0 = cv.coords(item)[1]
                anim.animar(cv, ("folha", item), 700,
                            lambda p: cv.coords(item, x, y0 + (y - y0) * p),
                            easing=lambda t: anim.ease_out_back(t, 1.1))
            self.after(120 + i * 140, chegar)

        self._subir_texto(self._titulo, 196, BRANCO, 180)
        self._subir_texto(self._sub, 254, SUAVE, 330)

        if self._feixe:
            self.after(900, self._varrer)

        anim.animar(cv, "progresso", DURACAO_MS, self._progresso,
                    ao_fim=self._concluir, easing=anim.ease_in_out_cubic)

    def _varrer(self):
        if not self._ok:
            return
        cv = self.cv
        x0, y0, x1, y1 = self._area_scan
        cx = (x0 + x1) / 2

        def quadro(p):
            cv.coords(self._feixe, cx, y0 - 10 + (y1 - y0 + 20) * p)
        anim.animar(cv, "feixe", 900, quadro, ao_fim=self._carimbar,
                    easing=anim.ease_in_out_cubic)

    def _carimbar(self):
        if not self._ok:
            return
        cv = self.cv
        cv.coords(self._feixe, -500, -500)
        xf, yf = self._selo_pos
        x_ini = xf - 120

        def quadro(p):
            cv.coords(self._selo, x_ini + (xf - x_ini) * p, yf)
        anim.animar(cv, "selo", 420, quadro, easing=lambda t: anim.ease_out_back(t, 1.5))

    def _progresso(self, p):
        if not self._ok:
            return
        self.cv.coords(self._barra, 0, ALTURA - 3, LARGURA * p, ALTURA)
        idx = min(int(p * (len(MENSAGENS) - 1)), len(MENSAGENS) - 2)
        self.cv.itemconfigure(self._msg, text=MENSAGENS[idx])

    def _concluir(self):
        if not self._ok:
            return
        self.cv.itemconfigure(self._msg, text=MENSAGENS[-1], fill=VERDE_CLARO)
        self.after(260, self._done)

    def _done(self):
        self._ok = False
        self.event_generate("<<SplashDone>>")

    def fechar(self):
        self._ok = False
        self.destroy()
