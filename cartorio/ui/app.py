"""Janela principal."""
import os
import re
import time
import tkinter as tk
from tkinter import ttk, messagebox

from .. import historico, tema
from ..config import carregar_preferencias, salvar_preferencias
from ..constantes import VERSAO, TIPOS, EXTENSOES_PADRAO
from ..renomeador import ignorar_temporariamente
from ..scanner import aquecer_powershell, encerrar_powershell
from ..tema import T, FONT_XS, aplicar_estilo_ttk, carregar_logo
from . import anim
from .aba_declaracao import AbaDeclaracao
from .aba_scanner import AbaScanner
from .configuracoes import TelaConfiguracoes
from .historico import JanelaHistorico
from .splash import SplashScreen
from .widgets import AbasDeslizantes, Botao, Notificador, Segmentado


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
        aquecer_powershell()
        if self._prefs["aba_principal"] in self._main_frames:
            self._sel_main(self._prefs["aba_principal"])
        splash = SplashScreen(self)
        splash.bind("<<SplashDone>>", lambda e: self._abrir(splash))


    # Toggle de tema 
    def _toggle_tema(self):
        tema.definir_tema("claro" if tema.tema_atual() == "escuro" else "escuro")
        self._prefs["tema"] = tema.tema_atual()
        salvar_preferencias(self._prefs)

        def _reconstruir():
            self._aplicar_tema_live()
            anim.surgir(self, 220)
        anim.sumir(self, _reconstruir, 140)

    # Scanner 

    def _bind_shortcuts(self):
        self.bind_all("<F5>",            lambda e: self._toggle_aba_ativa())
        self.bind_all("<F2>",            lambda e: self._verificar_aba_ativa())
        self.bind_all("<Control-o>",     lambda e: self._escolher_pasta_aba_ativa())
        self.bind_all("<Control-comma>", lambda e: self._abrir_configs())
        self.bind_all("<Control-l>",     lambda e: self._limpar_log())
        self.bind_all("<F1>",            lambda e: self._mostrar_atalhos())
        self.bind_all("<F7>",            lambda e: self._digitalizar_atalho())
        self.bind_all("<Control-z>",     lambda e: self._desfazer_ultima())
        self.bind_all("<Control-h>",     lambda e: self._abrir_historico())

    def _digitalizar_atalho(self):
        if self.grab_current() is None:
            self._sel_main("Scanner")
            self._aba_scanner.digitalizar()

    def trazer_para_frente(self):
        """Chamado quando outra instancia tenta abrir: mostra esta janela."""
        self.deiconify()
        if self.state() == "iconic":
            self.state("normal")
        self.lift()
        self.attributes("-topmost", True)
        self.after(300, lambda: self.attributes("-topmost", False))
        self.focus_force()

    # Historico

    def _abrir_historico(self):
        JanelaHistorico(self, self._desfazer_ultima)

    def _desfazer_ultima(self, confirmar=True, parent=None):
        """Reverte a ultima renomeacao (monitoramento ou lote). Retorna True se desfez."""
        parent = parent or self
        entrada = historico.ultima_desfazivel()
        if not entrada:
            messagebox.showinfo("Desfazer", "Não há renomeações para desfazer.", parent=parent)
            return False
        if confirmar and not messagebox.askyesno(
                "Desfazer última renomeação",
                f"Voltar {entrada['para']} para {entrada['de']}?\n\n"
                f"Pasta: {entrada['pasta']}\nRenomeado em: {entrada['data_hora']}",
                parent=parent):
            return False
        ok, msg = historico.desfazer(entrada, antes_de_renomear=ignorar_temporariamente)
        if not ok:
            messagebox.showerror("Desfazer", msg, parent=parent)
            self._log_global("Não foi possível desfazer: " + msg, "err")
            return False
        self._log_global("Desfeito: " + msg, "warn")
        self.notificar("Renomeação desfeita", msg, "aviso")
        aba = self.abas.get(entrada["tipo"])
        m = re.fullmatch(r"image(\d{6})\.\w+", entrada["para"], re.IGNORECASE)
        if aba and m:
            aba.devolver_numero(int(m.group(1)))
            aba._atualizar_contador_pasta()
        return True

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
            "F7          Digitalizar\n"
            "Ctrl+Z      Desfazer última renomeação\n"
            "Ctrl+H      Histórico\n"
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
                "handler":    aba.handler if aba.monitorando else None,
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
                aba.handler     = est["handler"]
                aba.handler.aba = aba   # o monitor passa a atualizar a aba nova
                aba.monitorando = True
                aba._visual_monitorando(True)
            if est["pasta"] and os.path.isdir(est["pasta"]):
                aba._atualizar_contador_pasta()
    def _abrir(self, splash):
        def _mostrar():
            splash.fechar()
            self.deiconify()
            self.lift()
            anim.surgir(self, 260)
        anim.sumir(splash, _mostrar, 180)
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
        encerrar_powershell()
        self.destroy()

    # UI
    def _build_ui(self):
        aplicar_estilo_ttk(self)
        self.notificar = Notificador(self).mostrar

        # Cabecalho
        hdr = tk.Frame(self, bg=T("SIDEBAR"))
        hdr.pack(fill="x")
        hi = tk.Frame(hdr, bg=T("SIDEBAR"), padx=24, pady=12)
        hi.pack(fill="x")
        try:
            self._logo_hdr = carregar_logo(52)
            tk.Label(hi, image=self._logo_hdr, bg=T("SIDEBAR")).pack(side="left")
        except Exception:
            tk.Label(hi, text="Cartório Santa Cruz", font=("Segoe UI", 13, "bold"),
                     bg=T("SIDEBAR"), fg=T("TEXT")).pack(side="left")
        tit = tk.Frame(hi, bg=T("SIDEBAR"))
        tit.pack(side="left", padx=(18, 0))
        tk.Label(tit, text="Renomeador de Declarações", font=("Segoe UI", 11, "bold"),
                 bg=T("SIDEBAR"), fg=T("TEXT"), anchor="w").pack(anchor="w")
        tk.Label(tit, text=f"Versão {VERSAO}", font=FONT_XS,
                 bg=T("SIDEBAR"), fg=T("MUTED"), anchor="w").pack(anchor="w")
        bf = tk.Frame(hi, bg=T("SIDEBAR"))
        bf.pack(side="right")
        tema_ico = "Modo claro" if tema.tema_atual() == "escuro" else "Modo escuro"
        for txt, cmd, dica in [(tema_ico, self._toggle_tema, "Alternar tema"),
                               ("Histórico", self._abrir_historico, "Renomeações e digitalizações  (Ctrl+H)"),
                               ("Configurações", self._abrir_configs, "Extensões, tempo de espera e início automático  (Ctrl+,)"),
                               ("Atalhos", self._mostrar_atalhos, "Atalhos de teclado  (F1)")]:
            Botao(bf, txt, cmd, variante="fantasma", dica=dica).pack(side="left", padx=(0, 2))
        tk.Frame(self, bg=T("BORDER"), height=1).pack(fill="x")

        # Rodape (antes do corpo para ficar sempre visivel)
        tk.Frame(self, bg=T("BORDER"), height=1).pack(fill="x", side="bottom")
        ft = tk.Frame(self, bg=T("SIDEBAR"), pady=6)
        ft.pack(fill="x", side="bottom")
        tk.Label(ft, text="Cartório Santa Cruz · 2º Subdistrito    Wesley Lucas Assunção",
                 font=FONT_XS, bg=T("SIDEBAR"), fg=T("MUTED")).pack()

        body = tk.Frame(self, bg=T("BG"))
        body.pack(fill="both", expand=True)

        # Abas principais com indicador deslizante e conteudo que entra deslizando
        self._main_tab_var = tk.StringVar(value="Renomeador")
        self._main_frames  = {}
        nomes_main = ["Renomeador", "Scanner"]
        main_content = tk.Frame(body, bg=T("BG"))

        def _ao_trocar(nome, anterior):
            self._main_tab_var.set(nome)
            novo = self._main_frames[nome]
            for n, f in self._main_frames.items():
                if n != nome:
                    f.place_forget()
            if anterior is None or anterior == nome:
                novo.place(x=0, y=0, relwidth=1, relheight=1)
            else:
                dx = 36 if nomes_main.index(nome) > nomes_main.index(anterior) else -36
                anim.animar(novo, "entrada", 240,
                            lambda p: novo.place(x=int(dx * (1 - p)), y=0, relwidth=1, relheight=1))
            novo.lift()
            if nome == "Scanner" and hasattr(self, "_aba_scanner"):
                self._aba_scanner.atualizar_info_destino()

        self._abas_main = AbasDeslizantes(body, nomes_main, _ao_trocar)
        self._abas_main.pack(fill="x")
        tk.Frame(body, bg=T("BORDER"), height=1).pack(fill="x")
        main_content.pack(fill="both", expand=True)
        for nome in nomes_main:
            self._main_frames[nome] = tk.Frame(main_content, bg=T("BG"))
        self._sel_main = lambda nome: self._abas_main.selecionar(nome)

        # Aba Renomeador
        ren_frame = self._main_frames["Renomeador"]
        ren_body  = tk.Frame(ren_frame, bg=T("BG"), padx=20, pady=14)
        ren_body.pack(fill="both", expand=True)

        sub_outer = tk.Frame(ren_body, bg=T("BG"))
        sub_outer.pack(fill="x")
        sub_bar = tk.Frame(sub_outer, bg=T("BG"))
        sub_bar.pack(fill="x", pady=(0, 10))
        sub_content = tk.Frame(sub_outer, bg=T("PANEL"),
                               highlightbackground=T("BORDER"), highlightthickness=1)
        sub_content.pack(fill="x")

        self.abas = {}
        self._tab_ativa_var = tk.StringVar(value=TIPOS[0])

        def _ao_tipo(tipo_sel):
            self._tab_ativa_var.set(tipo_sel)
            for tipo, aba in self.abas.items():
                if tipo == tipo_sel: aba.pack(fill="both", expand=True)
                else:                aba.pack_forget()
            if tipo_sel in self.abas:
                self.abas[tipo_sel].ao_exibir()

        self._seg_tipos = Segmentado(sub_bar, TIPOS, _ao_tipo)
        self._seg_tipos.pack(side="left")
        tk.Label(sub_bar, text="Cada tipo tem sua pasta e sua numeração.",
                 font=FONT_XS, bg=T("BG"), fg=T("MUTED")).pack(side="left", padx=14)
        for tipo in TIPOS:
            self.abas[tipo] = AbaDeclaracao(sub_content, tipo, self._log_global, self.get_prefs,
                                            notificar=lambda *a, **k: self.notificar(*a, **k))
        self._selecionar_aba = lambda tipo: self._seg_tipos.selecionar(tipo)
        self._seg_tipos.selecionar(TIPOS[0], animar=False)

        # Log
        lh = tk.Frame(ren_body, bg=T("BG"))
        lh.pack(fill="x", pady=(14, 6))
        tk.Label(lh, text="ATIVIDADE", font=("Segoe UI", 8, "bold"),
                 bg=T("BG"), fg=T("MUTED")).pack(side="left")
        Botao(lh, "Limpar", self._limpar_log, variante="secundario", tamanho="sm",
              dica="Limpar a lista  (Ctrl+L)").pack(side="right")
        Botao(lh, "Desfazer última", self._desfazer_ultima, variante="secundario", tamanho="sm",
              dica="Volta a última renomeação ao nome original  (Ctrl+Z)"
              ).pack(side="right", padx=(0, 6))
        lw = tk.Frame(ren_body, bg=T("LOG_BG"),
                      highlightbackground=T("BORDER"), highlightthickness=1)
        lw.pack(fill="both", expand=True)
        self.log_text = tk.Text(lw, font=("Consolas", 9),
                                bg=T("LOG_BG"), fg=T("LOG_FG"),
                                relief="flat", bd=0, state="disabled",
                                wrap="word", padx=12, pady=10, highlightthickness=0,
                                selectbackground=T("ACCENT"),
                                insertbackground=T("TEXT"), spacing1=2, spacing3=2)
        self.log_text.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(lw, orient="vertical", command=self.log_text.yview)
        sb.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.tag_config("ok",   foreground=T("OK"))
        self.log_text.tag_config("warn", foreground=T("WARN"))
        self.log_text.tag_config("err",  foreground=T("ERR"))
        self.log_text.tag_config("info", foreground=T("MUTED"))
        self.log_text.tag_config("hora", foreground=T("MUTED"))
        self.log_text.tag_config("vazio", foreground=T("MUTED"), justify="center",
                                 spacing1=40)
        self.log_text.tag_config("novo", background=T("NOTIF_BG"))
        self._log_vazio = False
        self._mostrar_log_vazio()

        # Aba Scanner
        scanner_frame = self._main_frames["Scanner"]
        self._aba_scanner = AbaScanner(scanner_frame, self._log_global,
                                       obter_aba=self.abas.get,
                                       notificar=lambda *a, **k: self.notificar(*a, **k))
        self._aba_scanner.pack(fill="both", expand=True)

        self.update_idletasks()
        self._abas_main.selecionar("Renomeador", animar=False)

    def _mostrar_log_vazio(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "As renomeações e digitalizações aparecem aqui.", "vazio")
        self.log_text.configure(state="disabled")
        self._log_vazio = True

    def _limpar_log(self):
        self._mostrar_log_vazio()

    def _log_global(self, msg, tag="info"):
        ts = time.strftime("%H:%M:%S")

        def _w():
            try:
                self.log_text.configure(state="normal")
            except tk.TclError:
                return
            if self._log_vazio:
                self.log_text.delete("1.0", "end")
                self._log_vazio = False
            inicio = self.log_text.index("end-1c")
            self.log_text.insert("end", f"{ts}   ", "hora")
            self.log_text.insert("end", f"{msg}\n", tag)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
            # Realce que desaparece na linha recem-chegada
            tag_linha = f"linha{id(msg)}{ts}"
            self.log_text.tag_add(tag_linha, inicio, "end-1c")
            base = T("LOG_BG")

            def quadro(p):
                try:
                    self.log_text.tag_config(tag_linha,
                                             background=anim.misturar(T("NOTIF_BG"), base, p))
                except tk.TclError:
                    pass
            anim.animar(self.log_text, tag_linha, 1200, quadro,
                        ao_fim=lambda: self.log_text.tag_delete(tag_linha),
                        easing=anim.ease_in_out_cubic)
        self.after(0, _w)

    def destroy(self): super().destroy()
