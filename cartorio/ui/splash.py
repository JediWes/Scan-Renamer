"""Tela de abertura."""
import tkinter as tk

from ..constantes import VERSAO
from ..tema import carregar_logo
from . import anim

# Cores fixas, independentes do tema
_SP_BG    = "#141617"
_SP_PANEL = "#2a3035"
_SP_MID   = "#2c3236"
_SP_LIGHT = "#2f9e5f"
_SP_MUTED = "#7a838a"
_SP_TEXT  = "#e7e9ea"

DURACAO_MS = 1500
MENSAGENS = ["Carregando configurações…", "Preparando monitoramento…", "Conectando ao scanner…"]


class SplashScreen(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(bg=_SP_MID)
        self.attributes("-topmost", True)
        W, H = 440, 300
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")
        inner = tk.Frame(self, bg=_SP_BG)
        inner.place(x=1, y=1, relwidth=1, relheight=1, width=-2, height=-2)

        lf = tk.Frame(inner, bg=_SP_BG)
        lf.pack(fill="x", padx=34, pady=(38, 0))
        try:
            self._li = carregar_logo(104, escuro=True)
            self._logo = tk.Label(lf, image=self._li, bg=_SP_BG)
        except Exception:
            self._logo = tk.Label(lf, text="Cartório Santa Cruz", font=("Segoe UI", 16, "bold"),
                                  bg=_SP_BG, fg=_SP_TEXT)
        self._logo.pack(anchor="w")
        self._titulo = tk.Label(inner, text="Renomeador de Declarações",
                                font=("Segoe UI", 11, "bold"), bg=_SP_BG, fg=_SP_BG, anchor="w")
        self._titulo.pack(fill="x", padx=34, pady=(18, 0))
        tk.Label(inner, text=f"Versão {VERSAO}", font=("Segoe UI", 8),
                 bg=_SP_BG, fg=_SP_MUTED, anchor="w").pack(fill="x", padx=34)

        self._cv = tk.Canvas(inner, height=3, bg=_SP_PANEL, highlightthickness=0, bd=0)
        self._cv.pack(fill="x", padx=34, pady=(26, 0))
        self._bar = self._cv.create_rectangle(0, 0, 0, 3, fill=_SP_LIGHT, width=0)
        self._mv = tk.StringVar(value=MENSAGENS[0])
        tk.Label(inner, textvariable=self._mv, font=("Segoe UI", 8),
                 bg=_SP_BG, fg=_SP_MUTED, anchor="w").pack(fill="x", padx=34, pady=(8, 0))
        tk.Label(inner, text="Wesley Lucas Assunção", font=("Segoe UI", 8),
                 bg=_SP_BG, fg=_SP_MID, anchor="e").pack(side="bottom", fill="x", padx=16, pady=10)

        self._ok = True
        anim.surgir(self, 220)
        self.update()
        # Titulo aparece com leve atraso, depois a barra avanca
        anim.animar(self._titulo, "fade", 420,
                    lambda p: self._titulo.configure(fg=anim.misturar(_SP_BG, _SP_TEXT, p)))
        anim.animar(self._cv, "progresso", DURACAO_MS, self._progresso,
                    ao_fim=self._concluir, easing=anim.ease_in_out_cubic)

    def _progresso(self, p):
        if not self._ok:
            return
        larg = self._cv.winfo_width()
        self._cv.coords(self._bar, 0, 0, int(larg * p), 3)
        self._mv.set(MENSAGENS[min(int(p * len(MENSAGENS)), len(MENSAGENS) - 1)])

    def _concluir(self):
        if not self._ok:
            return
        self._mv.set("Pronto")
        self.after(120, self._done)

    def _done(self):
        self._ok = False
        self.event_generate("<<SplashDone>>")

    def fechar(self):
        self._ok = False
        self.destroy()
