"""Janela de configuracoes."""
import tkinter as tk
from tkinter import messagebox

from ..tema import T, FONT, FONT_B, FONT_SM, FONT_XS
from ..constantes import EXTENSOES_PADRAO


class TelaConfiguracoes(tk.Toplevel):
    TODAS_EXTS = EXTENSOES_PADRAO

    def __init__(self, master, prefs, callback):
        super().__init__(master)
        self.title("Configurações")
        self.geometry("440x460")
        self.resizable(False, False)
        self.configure(bg=T("BG"))
        self.grab_set()
        self.callback = callback
        self.prefs    = dict(prefs)
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=T("ACCENT"), pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Configurações",
                 font=("Segoe UI", 11, "bold"),
                 bg=T("ACCENT"), fg=T("TEXT_ON_ACCENT")).pack()
        tk.Frame(self, bg=T("BORDER"), height=1).pack(fill="x")

        body = tk.Frame(self, bg=T("BG"), padx=26, pady=18)
        body.pack(fill="both", expand=True)

        # Delay
        self._sec(body, "DELAY ANTES DE RENOMEAR")
        self.delay_var = tk.DoubleVar(value=self.prefs.get("delay", 0.3))
        dr = tk.Frame(body, bg=T("BG"))
        dr.pack(fill="x", pady=(4, 16))
        tk.Scale(dr, variable=self.delay_var, from_=0.1, to=3.0, resolution=0.1,
                 orient="horizontal", bg=T("BG"), fg=T("TEXT"),
                 troughcolor=T("CARD"), highlightthickness=0,
                 activebackground=T("ACCENT"), length=300,
                 font=FONT_XS).pack(side="left")
        tk.Label(dr, textvariable=self.delay_var,
                 font=("Consolas", 10, "bold"),
                 bg=T("BG"), fg=T("SUBTEXT"), width=4).pack(side="left", padx=6)
        tk.Label(dr, text="s", font=FONT_SM,
                 bg=T("BG"), fg=T("MUTED")).pack(side="left")

        # Extensões
        tk.Frame(body, bg=T("SEP"), height=1).pack(fill="x", pady=(0, 14))
        self._sec(body, "EXTENSÕES MONITORADAS")
        ativas = set(self.prefs.get("extensoes", self.TODAS_EXTS))
        self.ext_vars = {}
        ef = tk.Frame(body, bg=T("BG"))
        ef.pack(fill="x", pady=(4, 16))
        for i, ext in enumerate(self.TODAS_EXTS):
            var = tk.BooleanVar(value=ext in ativas)
            self.ext_vars[ext] = var
            tk.Checkbutton(ef, text=ext, variable=var,
                           font=FONT_SM, bg=T("BG"), fg=T("TEXT"),
                           selectcolor=T("CARD"),
                           activebackground=T("BG"), activeforeground=T("TEXT"),
                           highlightthickness=0, bd=0
                           ).grid(row=i//4, column=i%4, sticky="w", padx=8, pady=3)

        # Tema
        tk.Frame(body, bg=T("SEP"), height=1).pack(fill="x", pady=(0, 14))
        self._sec(body, "TEMA DA INTERFACE")
        self.tema_var = tk.StringVar(value=self.prefs.get("tema", "escuro"))
        tr = tk.Frame(body, bg=T("BG"))
        tr.pack(fill="x", pady=(4, 0))
        for val, lbl, em in [("escuro","Escuro",""), ("claro","Claro","")]:
            f = tk.Frame(tr, bg=T("CARD"), padx=14, pady=8)
            f.pack(side="left", padx=(0, 10))
            tk.Radiobutton(f, text=lbl, variable=self.tema_var, value=val,
                           font=FONT_B, bg=T("CARD"), fg=T("TEXT"),
                           selectcolor=T("ACCENT"),
                           activebackground=T("CARD"), activeforeground=T("TEXT"),
                           highlightthickness=0).pack()

        # Botões
        # ── Auto-iniciar ──
        tk.Frame(body, bg=T("SEP"), height=1).pack(fill="x", pady=(14, 14))
        tk.Label(body, text="COMPORTAMENTO", font=("Segoe UI", 8, "bold"),
                 bg=T("BG"), fg=T("MUTED"), anchor="w").pack(fill="x", pady=(0, 6))
        self.autostart_var = tk.BooleanVar(value=self.prefs.get("auto_iniciar", False))
        f_auto = tk.Frame(body, bg=T("CARD"), padx=16, pady=10)
        f_auto.pack(fill="x")
        tk.Checkbutton(f_auto,
                       text="Iniciar monitoramento automaticamente ao abrir",
                       variable=self.autostart_var,
                       font=FONT,
                       bg=T("CARD"), fg=T("TEXT"),
                       selectcolor=T("ACCENT2"),
                       activebackground=T("CARD"), activeforeground=T("TEXT"),
                       highlightthickness=0, bd=0).pack(anchor="w")

        bf = tk.Frame(self, bg=T("BG"), padx=26, pady=12)
        bf.pack(fill="x")
        tk.Button(bf, text="Cancelar", font=FONT,
                  bg=T("BTN_SEC_BG"), fg=T("BTN_SEC_FG"),
                  relief="flat", cursor="hand2", padx=16, pady=8, bd=0,
                  activebackground=T("BORDER"), activeforeground=T("TEXT"),
                  command=self.destroy).pack(side="right", padx=(8, 0))
        tk.Button(bf, text="  Salvar  ", font=FONT_B,
                  bg=T("SUCCESS"), fg=T("TEXT_ON_ACCENT"),
                  relief="flat", cursor="hand2", padx=16, pady=8, bd=0,
                  activebackground=T("ACCENT2"), activeforeground=T("TEXT_ON_ACCENT"),
                  command=self._salvar).pack(side="right")

    def _sec(self, p, t):
        tk.Label(p, text=t, font=("Segoe UI", 8, "bold"),
                 bg=T("BG"), fg=T("MUTED"), anchor="w").pack(fill="x", pady=(0, 2))

    def _salvar(self):
        exts = [e for e, v in self.ext_vars.items() if v.get()]
        if not exts:
            messagebox.showwarning("Atenção", "Selecione ao menos uma extensão.", parent=self)
            return
        # Guarda dados e callback ANTES de destruir a janela
        novas = {"delay":        round(self.delay_var.get(), 1),
                 "extensoes":    exts,
                 "tema":         self.tema_var.get(),
                 "auto_iniciar": self.autostart_var.get()}
        cb = self.callback
        # Destrói a janela PRIMEIRO — evita que winfo_children() do App
        # a destrua no meio da execução ao chamar _aplicar_tema_live()
        self.destroy()
        # Agora chama o callback fora do contexto do Toplevel
        cb(novas)
