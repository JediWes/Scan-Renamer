"""Renomeacao em lote."""
import os
import re
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from ..tema import T, FONT_B, FONT_SM, FONT_XS
from .. import historico
from ..arquivos import listar_para_lote
from . import anim
from .widgets import Botao


class JanelaLote(tk.Toplevel):
    def __init__(self, master, tipo, pasta, extensoes, proximo_numero, callback_concluido):
        super().__init__(master)
        self.title(f"Renomear em Lote — {tipo}")
        self.geometry("620x500")
        self.configure(bg=T("BG"))
        self.grab_set()
        self.resizable(True, True)
        self.tipo      = tipo
        self.pasta     = pasta
        self.extensoes = extensoes
        self.num_inicio = proximo_numero
        self.callback  = callback_concluido
        self._rodando  = False
        self._arquivos = []
        self._build()
        self._escanear()

    def _build(self):
        tk.Label(self, text=f"Renomear em lote  ·  {self.tipo}", font=("Segoe UI", 12, "bold"),
                 bg=T("BG"), fg=T("TEXT"), anchor="w").pack(fill="x", padx=20, pady=(16, 0))

        body = tk.Frame(self, bg=T("BG"), padx=20, pady=14)
        body.pack(fill="both", expand=True)

        info = tk.Frame(body, bg=T("CARD"), padx=14, pady=10)
        info.pack(fill="x", pady=(0, 12))
        tk.Label(info, text=f"Pasta:  {self.pasta}", font=FONT_SM,
                 bg=T("CARD"), fg=T("TEXT"), anchor="w").pack(fill="x")
        self.lbl_info = tk.Label(info, text="Escaneando…", font=FONT_SM,
                                  bg=T("CARD"), fg=T("SUBTEXT"), anchor="w")
        self.lbl_info.pack(fill="x", pady=(4, 0))

        num_row = tk.Frame(body, bg=T("BG"))
        num_row.pack(fill="x", pady=(0, 12))
        tk.Label(num_row, text="Iniciar numeração em:", font=FONT_B,
                 bg=T("BG"), fg=T("TEXT")).pack(side="left", padx=(0, 10))
        self.num_var = tk.StringVar(value=f"image{self.num_inicio:06d}")
        tk.Entry(num_row, textvariable=self.num_var,
                 font=("Consolas", 12, "bold"),
                 bg=T("ENTRY_BG"), fg=T("OK"), insertbackground=T("OK"),
                 relief="flat", bd=0, width=14,
                 highlightbackground=T("BORDER"), highlightthickness=1
                 ).pack(side="left", ipady=6)

        tk.Label(body, text="Arquivos a renomear:", font=("Segoe UI", 8, "bold"),
                 bg=T("BG"), fg=T("MUTED"), anchor="w").pack(fill="x", pady=(0, 4))
        lf = tk.Frame(body, bg=T("LOG_BG"),
                       highlightbackground=T("BORDER"), highlightthickness=1)
        lf.pack(fill="both", expand=True, pady=(0, 12))
        self.listbox = tk.Listbox(lf, font=("Consolas", 9),
                                   bg=T("LOG_BG"), fg=T("LOG_FG"),
                                   selectbackground=T("ACCENT"),
                                   relief="flat", bd=0, activestyle="none")
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True, padx=8, pady=6)
        self.listbox.configure(yscrollcommand=sb.set)

        # Barra de progresso 100% tk puro
        self.prog_var = tk.DoubleVar(value=0)
        prog_outer = tk.Frame(body, bg=T("CARD"), height=18,
                              highlightbackground=T("BORDER"), highlightthickness=1)
        prog_outer.pack(fill="x", pady=(0, 8))
        prog_outer.pack_propagate(False)
        self._prog_canvas = tk.Canvas(prog_outer, height=18, bg=T("CARD"),
                                      highlightthickness=0)
        self._prog_canvas.pack(fill="both", expand=True)
        self._prog_bar = self._prog_canvas.create_rectangle(0, 0, 0, 18,
                                                             fill=T("ACCENT"), width=0)
        def _update_prog(*_):
            self._prog_canvas.update_idletasks()
            w = self._prog_canvas.winfo_width() or 1
            pct = self.prog_var.get() / 100
            self._prog_canvas.coords(self._prog_bar, 0, 0, int(w * pct), 18)
        self.prog_var.trace_add("write", _update_prog)
        self.lbl_prog = tk.Label(body, text="", font=FONT_XS,
                                  bg=T("BG"), fg=T("MUTED"))
        self.lbl_prog.pack()

        bf = tk.Frame(body, bg=T("BG"))
        bf.pack(fill="x", pady=(8, 0))
        Botao(bf, "Fechar", self.destroy, variante="secundario").pack(side="right", padx=(8, 0))
        self.btn_exec = Botao(bf, "Renomear todos", self._executar, largura=150)
        self.btn_exec.pack(side="right")
        self.bind("<Escape>", lambda e: self.destroy())
        anim.surgir(self)

    def _escanear(self):
        self._arquivos = listar_para_lote(self.pasta, set(self.extensoes))
        self.listbox.delete(0, "end")
        for f in self._arquivos:
            self.listbox.insert("end", f"  {f}")
        total = len(self._arquivos)
        self.lbl_info.configure(
            text=f"{total} arquivo{'s' if total != 1 else ''} encontrado{'s' if total != 1 else ''} para renomear")
        if total == 0:
            self.btn_exec.configure(state="disabled")

    def _executar(self):
        m = re.fullmatch(r"image(\d{6})", self.num_var.get().strip().lower())
        if not m:
            messagebox.showerror("Numeração inválida",
                                 "Use o formato: image + 6 dígitos", parent=self)
            return
        if not messagebox.askyesno(
            "Confirmar",
            f"Renomear {len(self._arquivos)} arquivo(s) a partir de {self.num_var.get()}?\n\n"
            "Cada renomeação fica no histórico e pode ser desfeita depois.",
            parent=self
        ): return
        self.btn_exec.configure(state="disabled")
        self._rodando = True
        threading.Thread(target=self._proc, args=(int(m.group(1)),), daemon=True).start()

    def _proc(self, numero):
        total = len(self._arquivos)
        renomeados = 0; erros = 0
        for i, nome in enumerate(self._arquivos):
            if not self._rodando: break
            orig = os.path.join(self.pasta, nome)
            if not os.path.exists(orig): continue
            ext = os.path.splitext(nome)[1].lower()
            while True:
                novo = f"image{numero:06d}{ext}"
                if not os.path.exists(os.path.join(self.pasta, novo)): break
                numero += 1
            try:
                os.rename(orig, os.path.join(self.pasta, novo))
                historico.registrar(historico.LOTE, self.tipo, self.pasta, nome, novo)
                renomeados += 1; numero += 1
                pct = int((i + 1) / total * 100)
                self.after(0, lambda p=pct, n=novo, o=nome:
                           self._upd(p, f"{o}  →  {n}"))
            except Exception as e:
                erros += 1
                self.after(0, lambda err=str(e): self._upd(None, f"Erro: {err}"))
            time.sleep(0.01)

        def _fim():
            self.prog_var.set(100)
            self.lbl_prog.configure(
                text=f"Concluído: {renomeados} renomeados, {erros} erros",
                fg=T("OK") if erros == 0 else T("WARN"))
            self.btn_exec.configure(state="disabled", text="Concluído")
            self.callback(numero)
        self.after(0, _fim)

    def _upd(self, pct, msg):
        if pct is not None: self.prog_var.set(pct)
        self.lbl_prog.configure(text=msg)
        self.listbox.insert("end", f"  {msg}")
        self.listbox.see("end")
