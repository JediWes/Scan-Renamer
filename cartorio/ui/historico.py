"""Janela de historico de renomeacoes e digitalizacoes."""
import os
import tkinter as tk
from tkinter import ttk, messagebox

from .. import historico
from ..tema import T, FONT_XS
from . import anim
from .widgets import Botao

ROTULO_ACAO = {
    historico.RENOMEAR: "Renomeado",
    historico.LOTE:     "Lote",
    historico.SCANNER:  "Digitalizado",
    historico.DESFAZER: "Desfeito",
}
LIMITE = 1000


class JanelaHistorico(tk.Toplevel):
    def __init__(self, master, desfazer):
        """desfazer(confirmar, parent) reverte a ultima renomeacao e retorna True se desfez."""
        super().__init__(master)
        self.title("Histórico")
        self.geometry("860x520")
        self.minsize(640, 360)
        self.configure(bg=T("BG"))
        self.transient(master)
        self._desfazer = desfazer
        self._build()
        self._carregar()
        self.bind("<Escape>", lambda e: self.destroy())
        anim.surgir(self)

    def _build(self):
        topo = tk.Frame(self, bg=T("BG"), padx=20, pady=14)
        topo.pack(fill="x")
        tk.Label(topo, text="Histórico", font=("Segoe UI", 12, "bold"),
                 bg=T("BG"), fg=T("TEXT")).pack(side="left")
        self._info = tk.Label(topo, text="", font=FONT_XS, bg=T("BG"), fg=T("MUTED"))
        self._info.pack(side="left", padx=(12, 0), pady=(4, 0))

        corpo = tk.Frame(self, bg=T("BG"), padx=20)
        corpo.pack(fill="both", expand=True)
        colunas = ("data", "acao", "tipo", "de", "para", "pasta")
        self.tv = ttk.Treeview(corpo, columns=colunas, show="headings", selectmode="browse")
        for col, titulo, larg, est in (("data", "Data e hora", 140, False),
                                       ("acao", "Ação", 90, False),
                                       ("tipo", "Tipo", 90, False),
                                       ("de", "De", 170, True),
                                       ("para", "Para", 140, True),
                                       ("pasta", "Pasta", 220, True)):
            self.tv.heading(col, text=titulo, anchor="w")
            self.tv.column(col, width=larg, minwidth=60, stretch=est, anchor="w")
        sb = ttk.Scrollbar(corpo, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tv.pack(side="left", fill="both", expand=True)
        self.tv.tag_configure("desfeito", foreground=T("MUTED"))
        self.tv.tag_configure("scanner", foreground=T("SUBTEXT"))

        rod = tk.Frame(self, bg=T("BG"), padx=20, pady=14)
        rod.pack(fill="x")
        Botao(rod, "Fechar", self.destroy, variante="secundario").pack(side="right")
        Botao(rod, "Abrir planilha (CSV)", self._abrir_csv, variante="secundario",
              dica="Abre o histórico completo no Excel").pack(side="right", padx=(0, 6))
        Botao(rod, "Desfazer última renomeação", self._desfazer_ultima,
              dica="Volta a última renomeação ao nome original  (Ctrl+Z)").pack(side="left")

    def _carregar(self):
        self.tv.delete(*self.tv.get_children())
        linhas = historico.ler()
        for ln in reversed(linhas[-LIMITE:]):
            acao = ln.get("acao", "")
            tag = ("desfeito",) if acao == historico.DESFAZER else (
                  ("scanner",) if acao == historico.SCANNER else ())
            self.tv.insert("", "end", tags=tag, values=(
                ln.get("data_hora", ""), ROTULO_ACAO.get(acao, acao), ln.get("tipo", ""),
                ln.get("de", ""), ln.get("para", ""), ln.get("pasta", "")))
        total = len(linhas)
        extra = f" (exibindo os {LIMITE} mais recentes)" if total > LIMITE else ""
        self._info.configure(text=f"{total} registro(s){extra}  ·  {historico.ARQUIVO}")

    def _desfazer_ultima(self):
        if self._desfazer(confirmar=True, parent=self):
            self._carregar()

    def _abrir_csv(self):
        if not os.path.exists(historico.ARQUIVO):
            messagebox.showinfo("Histórico", "Ainda não há registros.", parent=self)
            return
        try:
            os.startfile(historico.ARQUIVO)
        except (AttributeError, OSError) as e:
            messagebox.showerror("Histórico", f"Não foi possível abrir o arquivo:\n{e}", parent=self)
