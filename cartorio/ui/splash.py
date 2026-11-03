"""Tela de abertura."""
import tkinter as tk

from ..constantes import VERSAO
from ..tema import carregar_logo

# Cores fixas, independentes do tema
_SP_BG    = "#141617"
_SP_PANEL = "#2a3035"
_SP_MID   = "#2c3236"
_SP_LIGHT = "#2f9e5f"
_SP_MUTED = "#7a838a"
_SP_FOOT  = "#101213"

LOADING_MSGS = [
    "Iniciando módulo de monitoramento…", "Carregando configurações do sistema…",
    "Verificando permissões de pasta…",   "Preparando observador de arquivos…",
    "Carregando drivers de escaneamento…","Inicializando interface gráfica…",
    "Registrando extensões suportadas…",  "Configurando sistema de renomeação…",
    "Carregando módulo de log…",          "Verificando integridade dos módulos…",
    "Aplicando configurações de usuário…","Finalizando inicialização…",
]


class SplashScreen(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(bg=_SP_BG)
        self.attributes("-topmost", True)
        W, H = 460, 340
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        outer = tk.Frame(self, bg=_SP_MID, padx=1, pady=1)
        outer.place(relx=0, rely=0, relwidth=1, relheight=1)
        inner = tk.Frame(outer, bg=_SP_BG)
        inner.pack(side="left", fill="both", expand=True)
        lf = tk.Frame(inner, bg=_SP_BG)
        lf.pack(fill="x", padx=30, pady=(30, 0))
        try:
            self._li = carregar_logo(120, escuro=True)
            tk.Label(lf, image=self._li, bg=_SP_BG).pack(anchor="w")
        except Exception:
            tk.Label(lf, text="Cartório Sta Cruz  2° Subdistrito",
                     font=("Segoe UI", 15, "bold"), bg=_SP_BG, fg="#e7e9ea").pack(anchor="w")
        tk.Frame(inner, bg=_SP_MID, height=1).pack(fill="x", padx=30, pady=(14, 0))
        tk.Label(inner, text=f"RENOMEADOR DE DECLARAÇÕES  ·  v{VERSAO}",
                 font=("Segoe UI", 8, "bold"), bg=_SP_BG, fg=_SP_MUTED,
                 anchor="w").pack(fill="x", padx=30, pady=(8, 0))
        bar_bg = tk.Frame(inner, bg=_SP_PANEL, height=5)
        bar_bg.pack(fill="x", padx=30, pady=(22, 0))
        bar_bg.pack_propagate(False)
        self._cv = tk.Canvas(bar_bg, height=5, bg=_SP_PANEL, highlightthickness=0, bd=0)
        self._cv.pack(fill="both", expand=True)
        self._bar = self._cv.create_rectangle(0, 0, 0, 5, fill=_SP_LIGHT, width=0)
        self._mv = tk.StringVar(value=LOADING_MSGS[0])
        tk.Label(inner, textvariable=self._mv, font=("Segoe UI", 8),
                 bg=_SP_BG, fg=_SP_MUTED, anchor="w").pack(fill="x", padx=30, pady=(7, 0))
        ft = tk.Frame(inner, bg=_SP_FOOT)
        ft.pack(fill="x", side="bottom")
        tk.Label(ft, text="Cartório Santa Cruz  ·  2° Subdistrito",
                 font=("Segoe UI", 8), bg=_SP_FOOT, fg=_SP_MUTED,
                 anchor="w").pack(side="left", padx=14, pady=8)
        tk.Label(ft, text="by Wesley Lucas Assunção",
                 font=("Segoe UI", 8), bg=_SP_FOOT, fg=_SP_MUTED,
                 anchor="e").pack(side="right", padx=14, pady=8)
        self._p = 0.0; self._mi = 0; self._ok = True
        self.update()
        self._tick()

    def _tick(self):
        if not self._ok: return
        self._p = min(1.0, self._p + 0.005)
        self._cv.update_idletasks()
        larg = self._cv.winfo_width()
        self._cv.coords(self._bar, 0, 0, int(larg * self._p), 5)
        idx = min(int(self._p * len(LOADING_MSGS)), len(LOADING_MSGS)-1)
        if idx != self._mi:
            self._mi = idx
            self._mv.set(LOADING_MSGS[idx])
        if self._p < 1.0:
            self.after(30, self._tick)
        else:
            self._mv.set("Pronto!")
            self.after(300, self._done)

    def _done(self):
        self._ok = False
        self.event_generate("<<SplashDone>>")

    def fechar(self):
        self._ok = False
        self.destroy()
