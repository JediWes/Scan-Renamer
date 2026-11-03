"""Janela principal."""
import os
import time
import tkinter as tk
from tkinter import messagebox

from ..tema import T, FONT_SM, FONT_XS, carregar_logo

from .. import tema
from ..config import carregar_preferencias, salvar_preferencias
from ..constantes import VERSAO, TIPOS, EXTENSOES_PADRAO
from .aba_declaracao import AbaDeclaracao
from .aba_scanner import AbaScanner
from .configuracoes import TelaConfiguracoes
from .splash import SplashScreen


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        prefs = carregar_preferencias()
        tema.definir_tema(prefs.get("tema", "escuro"))
        self._prefs = {
            "delay":        prefs.get("delay", 0.3),
            "extensoes":    prefs.get("extensoes", EXTENSOES_PADRAO),
            "tema":         tema.tema_atual(),
            "auto_iniciar": prefs.get("auto_iniciar", False),
            "geometria":    prefs.get("geometria", "960x740"),
            "aba_principal": prefs.get("aba_principal", "Renomeador"),
        }
        self.withdraw()
        for cls in ("Button", "Checkbutton", "Menubutton"):
            self.option_add(f"*{cls}.highlightThickness", 0)
            self.option_add(f"*{cls}.borderWidth", 0)
        self.title("Renomeador de Declarações — Cartório Santa Cruz 2° Subdistrito")
        geo = self._prefs["geometria"]
        try:
            self.geometry(geo)
        except tk.TclError:
            self.geometry("960x740")
        self.minsize(840, 640)
        self.configure(bg=T("BG"))
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self._build_ui()
        self._bind_shortcuts()
        if self._prefs["aba_principal"] in self._main_frames:
            self._sel_main(self._prefs["aba_principal"])
        splash = SplashScreen(self)
        splash.bind("<<SplashDone>>", lambda e: self._abrir(splash))


    # Toggle de tema 
    def _toggle_tema(self):
        tema.definir_tema("claro" if tema.tema_atual() == "escuro" else "escuro")
        self._prefs["tema"] = tema.tema_atual()
        salvar_preferencias(self._prefs)
        self._aplicar_tema_live()

    # Scanner 

    def _bind_shortcuts(self):
        self.bind_all("<F5>",            lambda e: self._toggle_aba_ativa())
        self.bind_all("<F2>",            lambda e: self._verificar_aba_ativa())
        self.bind_all("<Control-o>",     lambda e: self._escolher_pasta_aba_ativa())
        self.bind_all("<Control-comma>", lambda e: self._abrir_configs())
        self.bind_all("<Control-l>",     lambda e: self._limpar_log())
        self.bind_all("<F1>",            lambda e: self._mostrar_atalhos())

    def _aba_ativa(self):
        return self.abas[self._tab_ativa_var.get()]

    def _toggle_aba_ativa(self):         self._aba_ativa()._toggle()
    def _verificar_aba_ativa(self):      self._aba_ativa()._verificar_numeracao()
    def _escolher_pasta_aba_ativa(self): self._aba_ativa()._escolher_pasta()

    def _mostrar_atalhos(self):
        messagebox.showinfo("Atalhos de Teclado",
            "F5          Iniciar / Parar monitoramento\n"
            "F2          Verificar numeração da pasta\n"
            "Ctrl+O      Escolher pasta\n"
            "Ctrl+,      Abrir configurações\n"
            "Ctrl+L      Limpar log\n"
            "F1          Esta janela", parent=self)

    # Configs
    def get_prefs(self): return dict(self._prefs)

    def _abrir_configs(self):
        TelaConfiguracoes(self, self._prefs, self._aplicar_prefs)

    def _aplicar_prefs(self, novas):
        # Preserva o tema atual (controlado pelo botão no header)
        novas["tema"] = tema.tema_atual()
        self._prefs.update(novas)
        salvar_preferencias(self._prefs)

    def _aplicar_tema_live(self):
        """Troca o tema sem nenhum Toplevel aberto."""
        # Salva estado antes de destruir
        aba_ativa  = self._tab_ativa_var.get()
        main_ativa = getattr(self, "_main_tab_var", tk.StringVar()).get() or "Renomeador"
        estados = {}
        for tipo, aba in self.abas.items():
            estados[tipo] = {
                "pasta":      aba.pasta_var.get(),
                "num":        aba.num_var.get(),
                "observer":   aba.observer if aba.monitorando else None,
                "monitorando":aba.monitorando,
                "proximo":    aba.proximo_numero,
                "total":      aba.total_renomeados,
                "ultimo":     aba._ultimo_caminho,
            }
            aba.monitorando = False
            aba.observer    = None

        # Sessao de scan em andamento sobrevive a reconstrucao da interface
        sc = self._aba_scanner
        sessao_scan = (sc._config_atual(), sc._tifs_sessao, sc._tmp_dir)
        sc._tmp_dir = None

        for w in list(self.winfo_children()):
            try:
                w.destroy()
            except Exception:
                pass
        self.configure(bg=T("BG"))
        self._build_ui()
        self._bind_shortcuts()

        cfg, tifs, tmp = sessao_scan
        sc = self._aba_scanner
        sc._aplicar_config(cfg)
        sc._tifs_sessao, sc._tmp_dir = tifs, tmp
        if tifs:
            sc._pags_var.set(str(len(tifs)) + " página(s) acumulada(s)")
        sc._atualizar_botoes_sessao()

        # Restaura aba principal
        if main_ativa in self._main_frames:
            self._sel_main(main_ativa)

        # Restaura sub-aba do renomeador
        if aba_ativa in self.abas:
            self._selecionar_aba(aba_ativa)

        # Restaura estado das abas
        for tipo, est in estados.items():
            aba = self.abas[tipo]
            aba.pasta_var.set(est["pasta"])
            aba.num_var.set(est["num"])
            aba.proximo_numero   = est["proximo"]
            aba.total_renomeados = est["total"]
            aba._ultimo_caminho  = est["ultimo"]
            if est["observer"]:
                aba.observer    = est["observer"]
                aba.monitorando = True
                aba.btn_var.set("Parar  [F5]")
                aba.btn.configure(bg=T("DANGER"), activebackground=T("DANGER_HOVER"))
                aba._dot.configure(bg=T("OK"))
                aba.lbl_status.configure(
                    text=f"Monitorando  ·  {os.path.basename(est['pasta'])}", fg=T("OK"))
            if est["pasta"] and os.path.isdir(est["pasta"]):
                aba._atualizar_contador_pasta()
    def _abrir(self, splash):
        splash.fechar(); self.deiconify(); self.lift()
        if self._prefs.get("auto_iniciar", False):
            self.after(600, self._auto_iniciar_todos)

    def _auto_iniciar_todos(self):
        for aba in self.abas.values():
            p = aba.pasta_var.get().strip()
            if p and os.path.isdir(p) and not aba.monitorando:
                aba._iniciar()

    def report_callback_exception(self, exc, val, tb):
        """Erros em callbacks do Tk aparecem no log em vez de sumir."""
        import traceback
        detalhe = "".join(traceback.format_exception(exc, val, tb))
        try:
            self._log_global(f"Erro interno: {val}", "err")
        except Exception:
            pass
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "erros.log"), "a", encoding="utf-8") as f:
                f.write(time.strftime("[%Y-%m-%d %H:%M:%S]\n") + detalhe + "\n")
        except Exception:
            pass
        messagebox.showerror("Erro", f"Ocorreu um erro inesperado:\n\n{val}", parent=self)

    def _fechar(self):
        pend = len(self._aba_scanner._tifs_sessao)
        if pend and not messagebox.askyesno(
                "Páginas não salvas",
                f"Há {pend} página(s) escaneada(s) sem salvar.\n\nFechar e descartar?",
                icon="warning", parent=self):
            return
        ativos = [t for t, a in self.abas.items() if a.monitorando]
        if ativos:
            if not messagebox.askyesno(
                "Monitoramento ativo",
                f"Ativo em: {', '.join(ativos)}\n\nFechar mesmo assim?",
                icon="warning"): return
        for aba in self.abas.values():
            if aba.monitorando: aba._parar()
            else:               aba._persistir()
        self._prefs["geometria"] = self.geometry()
        self._prefs["aba_principal"] = self._main_tab_var.get()
        salvar_preferencias(self._prefs)
        self._aba_scanner._limpar_sessao()
        self.destroy()

    # UI
    def _build_ui(self):
        # Cabecalho
        hdr = tk.Frame(self, bg=T("SIDEBAR"))
        hdr.pack(fill="x")
        hi = tk.Frame(hdr, bg=T("SIDEBAR"), padx=24, pady=12)
        hi.pack(fill="x")
        try:
            self._logo_hdr = carregar_logo(56)
            tk.Label(hi, image=self._logo_hdr, bg=T("SIDEBAR")).pack(side="left")
        except Exception:
            tk.Label(hi, text="Cartório Santa Cruz", font=("Segoe UI", 13, "bold"),
                     bg=T("SIDEBAR"), fg=T("TEXT")).pack(side="left")
        tk.Label(hi, text=f"Renomeador de Declarações  ·  v{VERSAO}",
                 font=FONT_SM, bg=T("SIDEBAR"), fg=T("MUTED")).pack(side="left", padx=(16, 0), pady=(14, 0))
        bf = tk.Frame(hi, bg=T("SIDEBAR"))
        bf.pack(side="right")
        tema_ico = "Modo claro" if tema.tema_atual() == "escuro" else "Modo escuro"
        for txt, cmd in [(tema_ico, self._toggle_tema),
                         ("Configurações", self._abrir_configs),
                         ("Atalhos", self._mostrar_atalhos)]:
            tk.Button(bf, text=txt, font=FONT_SM,
                      bg=T("SIDEBAR"), fg=T("HDR_FG"),
                      relief="flat", cursor="hand2", padx=10, pady=5, bd=0,
                      activebackground=T("ACCENT2"), activeforeground=T("TEXT"),
                      command=cmd).pack(side="left", padx=(0, 2))
        tk.Frame(self, bg=T("BORDER"), height=1).pack(fill="x")

        body = tk.Frame(self, bg=T("BG"))
        body.pack(fill="both", expand=True)

        # Abas principais: Renomeador / Scanner
        main_tab_bar = tk.Frame(body, bg=T("SIDEBAR"))
        main_tab_bar.pack(fill="x")
        tk.Frame(body, bg=T("BORDER"), height=1).pack(fill="x")
        main_content = tk.Frame(body, bg=T("BG"))
        main_content.pack(fill="both", expand=True)

        self._main_tab_var  = tk.StringVar(value="Renomeador")
        self._main_tab_btns = {}
        self._main_ind      = {}
        self._main_frames   = {}

        def _sel_main(nome):
            self._main_tab_var.set(nome)
            for n, f in self._main_frames.items():
                if n == nome: f.pack(fill="both", expand=True)
                else:         f.pack_forget()
            for n, b in self._main_tab_btns.items():
                ativo = n == nome
                b.configure(bg=T("SIDEBAR"),
                            fg=T("TEXT") if ativo else T("MUTED"),
                            font=("Segoe UI", 10, "bold") if ativo else ("Segoe UI", 10))
                self._main_ind[n].configure(bg=T("ACCENT") if ativo else T("SIDEBAR"))
        self._sel_main = _sel_main

        for nome in ["Renomeador", "Scanner"]:
            col = tk.Frame(main_tab_bar, bg=T("SIDEBAR"))
            col.pack(side="left", padx=(20 if nome == "Renomeador" else 0, 0))
            b = tk.Button(col, text=nome, font=("Segoe UI", 10),
                          bg=T("SIDEBAR"), fg=T("MUTED"),
                          relief="flat", bd=0, padx=14, pady=9, cursor="hand2",
                          activebackground=T("SIDEBAR"), activeforeground=T("TEXT"),
                          command=lambda n=nome: _sel_main(n))
            b.pack()
            ind = tk.Frame(col, bg=T("SIDEBAR"), height=2)
            ind.pack(fill="x")
            self._main_tab_btns[nome] = b
            self._main_ind[nome]     = ind
            f = tk.Frame(main_content, bg=T("BG"))
            self._main_frames[nome] = f

        # Aba Renomeador
        ren_frame = self._main_frames["Renomeador"]
        ren_body  = tk.Frame(ren_frame, bg=T("BG"), padx=20, pady=12)
        ren_body.pack(fill="both", expand=True)

        # Sub-abas: Nascimento / Obito / Natimorto
        sub_outer  = tk.Frame(ren_body, bg=T("BG"))
        sub_outer.pack(fill="x")
        sub_bar    = tk.Frame(sub_outer, bg=T("BG"))
        sub_bar.pack(fill="x", pady=(0, 10))
        seg = tk.Frame(sub_bar, bg=T("CARD"), padx=3, pady=3)
        seg.pack(side="left")
        sub_content = tk.Frame(sub_outer, bg=T("PANEL"),
                               highlightbackground=T("BORDER"), highlightthickness=1)
        sub_content.pack(fill="x")

        self.abas      = {}
        self._tab_btns = {}
        self._tab_ativa_var = tk.StringVar(value=TIPOS[0])

        def _selecionar_aba(tipo_sel):
            self._tab_ativa_var.set(tipo_sel)
            for tipo, aba in self.abas.items():
                if tipo == tipo_sel: aba.pack(fill="both", expand=True)
                else:                aba.pack_forget()
            for tipo, btn in self._tab_btns.items():
                if tipo == tipo_sel:
                    btn.configure(bg=T("ACCENT"), fg=T("TEXT_ON_ACCENT"),
                                  font=("Segoe UI", 10, "bold"))
                else:
                    btn.configure(bg=T("CARD"), fg=T("SUBTEXT"),
                                  font=("Segoe UI", 10))

        for tipo in TIPOS:
            btn = tk.Button(seg, text=tipo, font=("Segoe UI", 10),
                            bg=T("CARD"), fg=T("SUBTEXT"),
                            relief="flat", bd=0, padx=18, pady=6, cursor="hand2",
                            activebackground=T("ACCENT2"), activeforeground=T("TEXT"),
                            command=lambda t=tipo: _selecionar_aba(t))
            btn.pack(side="left")
            self._tab_btns[tipo] = btn
            aba = AbaDeclaracao(sub_content, tipo, self._log_global, self.get_prefs)
            self.abas[tipo] = aba
        self._selecionar_aba = _selecionar_aba
        _selecionar_aba(TIPOS[0])

        # Log
        lh = tk.Frame(ren_body, bg=T("BG"))
        lh.pack(fill="x", pady=(12, 4))
        tk.Label(lh, text="LOG DE ATIVIDADE  [Ctrl+L]",
                 font=("Segoe UI", 8, "bold"), bg=T("BG"), fg=T("MUTED")).pack(side="left")
        tk.Button(lh, text="Limpar", font=FONT_XS,
                  bg=T("BTN_SEC_BG"), fg=T("BTN_SEC_FG"),
                  relief="flat", cursor="hand2", padx=8, pady=2, bd=0,
                  activebackground=T("ACCENT"), activeforeground="white",
                  command=self._limpar_log).pack(side="right")
        lw = tk.Frame(ren_body, bg=T("LOG_BG"),
                      highlightbackground=T("BORDER"), highlightthickness=1)
        lw.pack(fill="both", expand=True)
        self.log_text = tk.Text(lw, font=("Consolas", 9),
                                bg=T("LOG_BG"), fg=T("LOG_FG"),
                                relief="flat", bd=0, state="disabled",
                                wrap="word", padx=12, pady=10, highlightthickness=0,
                                selectbackground=T("ACCENT"),
                                insertbackground=T("TEXT"))
        self.log_text.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(lw, orient="vertical", command=self.log_text.yview,
                          bg=T("CARD"), troughcolor=T("BG"),
                          activebackground=T("ACCENT"), relief="flat", bd=0)
        sb.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.tag_config("ok",   foreground=T("OK"))
        self.log_text.tag_config("warn", foreground=T("WARN"))
        self.log_text.tag_config("err",  foreground=T("ERR"))
        self.log_text.tag_config("info", foreground=T("MUTED"))

        # Aba Scanner 
        scanner_frame = self._main_frames["Scanner"]
        self._aba_scanner = AbaScanner(scanner_frame, self._log_global)
        self._aba_scanner.pack(fill="both", expand=True)

        # Seleciona Renomeador por padrão
        _sel_main("Renomeador")

        # Rodape
        tk.Frame(self, bg=T("BORDER"), height=1).pack(fill="x", side="bottom")
        ft = tk.Frame(self, bg=T("SIDEBAR"), pady=6)
        ft.pack(fill="x", side="bottom")
        tk.Label(ft, text="Cartório Santa Cruz · 2º Subdistrito    Wesley Lucas Assunção",
                 font=FONT_XS, bg=T("SIDEBAR"), fg=T("MUTED")).pack()

    def _limpar_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _log_global(self, msg, tag="info"):
        ts = time.strftime("%H:%M:%S")
        def _w():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"[{ts}]  {msg}\n", tag)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _w)

    def destroy(self): super().destroy()
