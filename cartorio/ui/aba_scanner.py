"""Aba de digitalizacao."""
import os
import re
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from ..tema import T, FONT_SM, FONT_XS

from ..config import carregar_presets, salvar_presets, PRESET_ULTIMO
from ..scanner import (MODOS_COR_LABEL, scanner_listar_dispositivos,
                       scanner_uma_pagina, tifs_para_pdf)


class AbaScanner(tk.Frame):
    RESOLUCOES = ["100","150","200","300","400","600"]
    MODOS_COR  = list(MODOS_COR_LABEL)

    def __init__(self, parent, log_callback):
        super().__init__(parent, bg=T("BG"))
        self.log_cb        = log_callback
        self._presets      = carregar_presets()
        self._dispositivos = []
        self._dev_id       = ""
        self._tifs_sessao  = []
        self._tmp_dir      = None
        self._build()
        self._atualizar_menu_presets()
        self._aplicar_config(self._presets.get(PRESET_ULTIMO, {}))
        self.after(300, self._detectar_dispositivos)

    def _build(self):
        main = tk.Frame(self, bg=T("BG"), padx=20, pady=16)
        main.pack(fill="both", expand=True)
        left  = tk.Frame(main, bg=T("BG"))
        left.pack(side="left", fill="both", expand=True, padx=(0, 20))
        right = tk.Frame(main, bg=T("BG"), width=260)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # Scanner detectado
        self._sec(left, "SCANNER DETECTADO")
        dev_row = tk.Frame(left, bg=T("BG"))
        dev_row.pack(fill="x", pady=(4, 12))
        self.dev_var = tk.StringVar(value="Detectando...")
        self._dev_lbl = tk.Label(dev_row, textvariable=self.dev_var,
                                  font=FONT_SM, bg=T("CARD"), fg=T("SUBTEXT"),
                                  padx=10, pady=6, anchor="w", relief="flat")
        self._dev_lbl.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(dev_row, text="Detectar", font=FONT_XS,
                  bg=T("ACCENT"), fg=T("TEXT_ON_ACCENT"),
                  relief="flat", cursor="hand2", padx=10, pady=5, bd=0,
                  activebackground=T("ACCENT2"),
                  command=self._detectar_dispositivos).pack(side="right")

        tk.Frame(left, bg=T("SEP"), height=1).pack(fill="x", pady=(0, 12))

        # Presets
        self._sec(left, "PRESETS")
        pr = tk.Frame(left, bg=T("BG"))
        pr.pack(fill="x", pady=(4, 12))
        self.preset_var = tk.StringVar(value="-- manual --")
        self._preset_menu = tk.OptionMenu(pr, self.preset_var, "-- manual --",
                                           command=self._carregar_preset)
        self._preset_menu.configure(
            font=FONT_SM, bg=T("ENTRY_BG"), fg=T("TEXT"),
            activebackground=T("ACCENT"), activeforeground=T("TEXT_ON_ACCENT"),
            relief="flat", bd=0, highlightthickness=0, indicatoron=True, padx=8)
        self._preset_menu["menu"].configure(
            bg=T("CARD"), fg=T("TEXT"), font=FONT_SM,
            activebackground=T("ACCENT"), activeforeground=T("TEXT_ON_ACCENT"))
        self._preset_menu.pack(side="left", fill="x", expand=True, padx=(0, 6))
        tk.Button(pr, text="Salvar preset", font=FONT_XS,
                  bg=T("BTN_SEC_BG"), fg=T("BTN_SEC_FG"),
                  relief="flat", cursor="hand2", padx=8, pady=5, bd=0,
                  activebackground=T("ACCENT"), activeforeground=T("TEXT_ON_ACCENT"),
                  command=self._salvar_preset).pack(side="left", padx=(0, 4))
        tk.Button(pr, text="X", font=("Segoe UI", 9, "bold"),
                  bg=T("DANGER"), fg=T("TEXT_ON_ACCENT"),
                  relief="flat", cursor="hand2", padx=8, pady=5, bd=0,
                  command=self._excluir_preset).pack(side="left")

        tk.Frame(left, bg=T("SEP"), height=1).pack(fill="x", pady=(0, 12))

        # Configuracoes
        self._sec(left, "CONFIGURAÇÕES DE DIGITALIZAÇÃO")
        grid = tk.Frame(left, bg=T("BG"))
        grid.pack(fill="x", pady=(6, 0))
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(3, weight=1)

        def lbl(txt, row, col):
            tk.Label(grid, text=txt, font=FONT_XS, bg=T("BG"), fg=T("MUTED"),
                     anchor="w").grid(row=row, column=col, sticky="w", padx=(0,8), pady=5)

        def opt(var, ops, row, col, w=14):
            m = tk.OptionMenu(grid, var, *ops)
            m.configure(font=FONT_SM, bg=T("ENTRY_BG"), fg=T("TEXT"),
                        activebackground=T("ACCENT"), activeforeground=T("TEXT_ON_ACCENT"),
                        relief="flat", bd=0, highlightthickness=0, width=w, padx=4)
            m["menu"].configure(bg=T("CARD"), fg=T("TEXT"), font=FONT_SM,
                                activebackground=T("ACCENT"), activeforeground=T("TEXT_ON_ACCENT"))
            m.grid(row=row, column=col, sticky="ew", pady=5)
            return m

        lbl("Resolução (DPI):", 0, 0)
        self.res_var = tk.StringVar(value="300")
        opt(self.res_var, self.RESOLUCOES, 0, 1)
        lbl("Modo de cor:", 0, 2)
        self.cor_var = tk.StringVar(value="Colorido")
        opt(self.cor_var, self.MODOS_COR, 0, 3)

        lbl("Frente e verso:", 1, 0)
        self.duplex_var = tk.BooleanVar(value=False)
        df = tk.Frame(grid, bg=T("BG"))
        df.grid(row=1, column=1, sticky="w", pady=5)
        tk.Checkbutton(df, variable=self.duplex_var, text="Ativado",
                       font=FONT_SM, bg=T("BG"), fg=T("TEXT"),
                       selectcolor=T("ACCENT2"), activebackground=T("BG"),
                       highlightthickness=0, bd=0).pack(anchor="w")

        lbl("Múltiplas páginas:", 1, 2)
        self.multipag_var = tk.BooleanVar(value=False)
        mf = tk.Frame(grid, bg=T("BG"))
        mf.grid(row=1, column=3, sticky="w", pady=5)
        tk.Checkbutton(mf, variable=self.multipag_var, text="Ativado",
                       font=FONT_SM, bg=T("BG"), fg=T("TEXT"),
                       selectcolor=T("ACCENT2"), activebackground=T("BG"),
                       highlightthickness=0, bd=0).pack(anchor="w")

        lbl("Nome do arquivo:", 2, 0)
        self.perg_nome_var = tk.BooleanVar(value=False)
        nf = tk.Frame(grid, bg=T("BG"))
        nf.grid(row=2, column=1, columnspan=3, sticky="w", pady=5)
        tk.Checkbutton(nf, variable=self.perg_nome_var,
                       text="Perguntar o nome ao salvar o PDF",
                       font=FONT_SM, bg=T("BG"), fg=T("TEXT"),
                       selectcolor=T("ACCENT2"), activebackground=T("BG"),
                       highlightthickness=0, bd=0).pack(anchor="w")

        tk.Frame(left, bg=T("SEP"), height=1).pack(fill="x", pady=(14, 12))

        # Pasta destino
        self._sec(left, "PASTA DE DESTINO")
        dest_row = tk.Frame(left, bg=T("BG"))
        dest_row.pack(fill="x", pady=(4, 0))
        self.dest_var = tk.StringVar(value="")
        tk.Entry(dest_row, textvariable=self.dest_var,
                 font=FONT_SM, bg=T("ENTRY_BG"), fg=T("TEXT"),
                 insertbackground=T("TEXT"), relief="flat", bd=0,
                 highlightbackground=T("BORDER"), highlightthickness=1
                 ).pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))
        tk.Button(dest_row, text="...", font=("Segoe UI", 11),
                  bg=T("ACCENT"), fg=T("TEXT_ON_ACCENT"),
                  relief="flat", cursor="hand2", padx=10, pady=5, bd=0,
                  activebackground=T("ACCENT2"),
                  command=self._escolher_pasta).pack(side="right")

        # Coluna direita: botao + status
        tk.Frame(right, bg=T("BG"), height=20).pack()
        self._btn_scan = tk.Button(right, text="Digitalizar",
                                    font=("Segoe UI", 14, "bold"),
                                    bg=T("SUCCESS"), fg=T("TEXT_ON_ACCENT"),
                                    relief="flat", cursor="hand2",
                                    padx=20, pady=40, bd=0,
                                    activebackground=T("ACCENT2"),
                                    activeforeground=T("TEXT_ON_ACCENT"),
                                    command=self._iniciar_sessao)
        self._btn_scan.pack(fill="x", padx=10, pady=(0, 16))

        status_frame = tk.Frame(right, bg=T("CARD"),
                                highlightbackground=T("BORDER"), highlightthickness=1)
        status_frame.pack(fill="x", padx=10, pady=(0, 8))
        self._dot = tk.Frame(status_frame, bg=T("MUTED"), width=4)
        self._dot.pack(side="left", fill="y")
        self._status_var = tk.StringVar(value="Aguardando...")
        tk.Label(status_frame, textvariable=self._status_var,
                 font=FONT_XS, bg=T("CARD"), fg=T("SUBTEXT"),
                 wraplength=200, justify="left", padx=8, pady=8).pack(side="left")

        self._pags_var = tk.StringVar(value="")
        tk.Label(right, textvariable=self._pags_var,
                 font=("Consolas", 9, "bold"),
                 bg=T("BG"), fg=T("OK")).pack(padx=10, anchor="w")

        # Acoes da sessao: permitem concluir ou descartar paginas acumuladas
        acoes = tk.Frame(right, bg=T("BG"))
        acoes.pack(fill="x", padx=10, pady=(8, 0))
        self._btn_concluir = tk.Button(acoes, text="Salvar PDF agora", font=FONT_SM,
                                       bg=T("ACCENT"), fg=T("TEXT_ON_ACCENT"),
                                       relief="flat", cursor="hand2", padx=10, pady=6, bd=0,
                                       activebackground=T("ACCENT2"),
                                       activeforeground=T("TEXT_ON_ACCENT"),
                                       command=self._finalizar_pdf, state="disabled",
                                       disabledforeground=T("MUTED"))
        self._btn_concluir.pack(fill="x", pady=(0, 4))
        self._btn_descartar = tk.Button(acoes, text="Descartar páginas", font=FONT_SM,
                                        bg=T("BTN_SEC_BG"), fg=T("BTN_SEC_FG"),
                                        relief="flat", cursor="hand2", padx=10, pady=6, bd=0,
                                        activebackground=T("DANGER"),
                                        activeforeground=T("TEXT_ON_ACCENT"),
                                        command=self._descartar_sessao, state="disabled",
                                        disabledforeground=T("MUTED"))
        self._btn_descartar.pack(fill="x")
        self._atualizar_botoes_sessao()

    def _sec(self, p, t):
        tk.Label(p, text=t, font=("Segoe UI", 8, "bold"),
                 bg=T("BG"), fg=T("MUTED"), anchor="w").pack(fill="x", pady=(0, 2))

    def _escolher_pasta(self):
        p = filedialog.askdirectory(title="Pasta de destino para os scans",
                                    initialdir=self.dest_var.get() or None,
                                    parent=self.winfo_toplevel())
        if p:
            self.dest_var.set(os.path.normpath(p))
            self._salvar_ultimo()

    def _detectar_dispositivos(self):
        self.dev_var.set("Detectando...")
        self._btn_scan.configure(state="disabled")
        def _busca():
            devs = scanner_listar_dispositivos()
            def _ui():
                self._dispositivos = devs
                if devs:
                    idx = next(
                        (i for i, (n, _) in enumerate(devs)
                         if "brother" in n.lower() or "ds-940" in n.lower()
                         or "ds940" in n.lower()), 0)
                    nome, did = devs[idx]
                    self._dev_id = did
                    self.dev_var.set(nome)
                    self._dev_lbl.configure(fg=T("SUBTEXT"))
                    self._dot.configure(bg=T("OK"))
                    self._btn_scan.configure(state="normal")
                else:
                    self.dev_var.set("Nenhum scanner encontrado")
                    self._dev_lbl.configure(fg=T("ERR"))
                    self._dot.configure(bg=T("DANGER"))
                    self._dev_id = ""
            self.after(0, _ui)
        threading.Thread(target=_busca, daemon=True).start()

    def _atualizar_menu_presets(self):
        menu = self._preset_menu["menu"]
        menu.delete(0, "end")
        menu.add_command(label="-- manual --",
                         command=lambda: self.preset_var.set("-- manual --"))
        for nome in sorted(k for k in self._presets if k != PRESET_ULTIMO):
            menu.add_command(label=nome,
                             command=lambda n=nome: self._carregar_preset(n))

    def _config_atual(self):
        return {
            "resolucao":  int(self.res_var.get()),
            "cor":        self.cor_var.get(),
            "duplex":     self.duplex_var.get(),
            "multipag":   self.multipag_var.get(),
            "perg_nome":  self.perg_nome_var.get(),
            "pasta":      self.dest_var.get().strip(),
        }

    def _aplicar_config(self, p):
        if not p:
            return
        res = str(p.get("resolucao", "300"))
        self.res_var.set(res if res in self.RESOLUCOES else "300")
        cor = p.get("cor", "Colorido")
        self.cor_var.set(cor if cor in MODOS_COR_LABEL else "Colorido")
        self.duplex_var.set(bool(p.get("duplex", False)))
        self.multipag_var.set(bool(p.get("multipag", False)))
        self.perg_nome_var.set(bool(p.get("perg_nome", False)))
        pasta = p.get("pasta", "")
        if pasta:
            self.dest_var.set(pasta)

    def _salvar_ultimo(self):
        self._presets[PRESET_ULTIMO] = self._config_atual()
        salvar_presets(self._presets)

    def _carregar_preset(self, nome):
        if nome == "-- manual --" or nome not in self._presets:
            return
        self.preset_var.set(nome)
        self._aplicar_config(self._presets[nome])
        pasta = self.dest_var.get().strip()
        if pasta and not os.path.isdir(pasta):
            self._set_status("Pasta do preset não encontrada: " + pasta, T("WARN"))
        else:
            self._set_status("Preset carregado: " + nome)

    def _salvar_preset(self):
        nome = simpledialog.askstring("Salvar preset", "Nome do preset:",
                                      initialvalue=self.preset_var.get()
                                      if self.preset_var.get() != "-- manual --" else "",
                                      parent=self.winfo_toplevel())
        if not nome or not nome.strip():
            return
        nome = nome.strip()
        if nome == PRESET_ULTIMO:
            return
        if not self.dest_var.get().strip():
            if not messagebox.askyesno("Preset sem pasta",
                                       "Nenhuma pasta de destino definida.\n"
                                       "Salvar o preset assim mesmo?",
                                       parent=self.winfo_toplevel()):
                return
        self._presets[nome] = self._config_atual()
        salvar_presets(self._presets)
        self._atualizar_menu_presets()
        self.preset_var.set(nome)
        self._set_status("Preset salvo: " + nome)

    def _excluir_preset(self):
        nome = self.preset_var.get()
        if nome == "-- manual --" or nome not in self._presets:
            return
        if not messagebox.askyesno("Excluir", "Excluir preset " + nome + "?",
                                    parent=self.winfo_toplevel()):
            return
        del self._presets[nome]
        salvar_presets(self._presets)
        self._atualizar_menu_presets()
        self.preset_var.set("-- manual --")
        self._set_status("Preset excluido.")

    def _set_status(self, txt, cor=None):
        self._status_var.set(txt)
        if cor:
            self._dot.configure(bg=cor)

    def _limpar_sessao(self):
        import shutil
        self._tifs_sessao = []
        if self._tmp_dir and os.path.isdir(self._tmp_dir):
            try:
                shutil.rmtree(self._tmp_dir, ignore_errors=True)
            except Exception:
                pass
        self._tmp_dir = None
        self._pags_var.set("")
        self._atualizar_botoes_sessao()

    def _atualizar_botoes_sessao(self, ocupado=False):
        tem = bool(self._tifs_sessao)
        ativo = tem and not ocupado
        self._btn_concluir.configure(state="normal" if ativo else "disabled",
                                     bg=T("ACCENT") if ativo else T("CARD"))
        self._btn_descartar.configure(state="normal" if ativo else "disabled")

    def _descartar_sessao(self):
        n = len(self._tifs_sessao)
        if not n:
            return
        if not messagebox.askyesno("Descartar páginas",
                                   f"Descartar {n} página(s) acumulada(s)?",
                                   parent=self.winfo_toplevel()):
            return
        self._limpar_sessao()
        self._set_status("Páginas descartadas.")

    def _iniciar_sessao(self):
        pasta = self.dest_var.get().strip()
        if not pasta or not os.path.isdir(pasta):
            messagebox.showerror("Pasta inválida",
                                 "Selecione uma pasta de destino existente antes de escanear.",
                                 parent=self.winfo_toplevel())
            return
        self._salvar_ultimo()
        import tempfile
        if self._tmp_dir is None:
            self._tmp_dir = tempfile.mkdtemp(prefix="scan_")
            self._tifs_sessao = []
        self._btn_scan.configure(state="disabled")
        self._atualizar_botoes_sessao(ocupado=True)
        self._set_status("Digitalizando…", T("WARN"))
        self.update()
        modo_cor  = MODOS_COR_LABEL.get(self.cor_var.get(), 'cor')
        res       = int(self.res_var.get())
        duplex    = self.duplex_var.get()
        multipag  = self.multipag_var.get()
        device_id = self._dev_id
        n_pag     = len(self._tifs_sessao) + 1
        nome_arq  = "pag_" + str(n_pag).zfill(3)
        def _run():
            try:
                novos = scanner_uma_pagina(
                    tmp_dir      = self._tmp_dir,
                    nome_arquivo = nome_arq,
                    resolucao    = res,
                    modo_cor     = modo_cor,
                    duplex       = duplex,
                    device_id    = device_id,
                )
                self._tifs_sessao.extend(novos)
                def _pos_scan():
                    n = len(self._tifs_sessao)
                    self._pags_var.set(str(n) + " página(s) acumulada(s)")
                    self._btn_scan.configure(state="normal")
                    self._atualizar_botoes_sessao()
                    if multipag:
                        msg = (str(n) + " página(s) acumulada(s).\n\n"
                               "Sim: escanear a próxima página\n"
                               "Não: salvar o PDF agora")
                        continuar = messagebox.askyesno("Continuar?", msg,
                                                         parent=self.winfo_toplevel())
                        if continuar:
                            self._set_status("Escaneando a próxima página…", T("WARN"))
                            self._iniciar_sessao()
                        else:
                            self._finalizar_pdf()
                    else:
                        self._finalizar_pdf()
                self.after(0, _pos_scan)
            except Exception as e:
                msg = str(e)
                def _err():
                    self._btn_scan.configure(state="normal")
                    self._atualizar_botoes_sessao()
                    self._set_status("Erro: " + msg[:60], T("DANGER"))
                    messagebox.showerror("Erro no scanner",
                                         "Falha ao digitalizar:\n\n" + msg,
                                         parent=self.winfo_toplevel())
                self.after(0, _err)
        threading.Thread(target=_run, daemon=True).start()

    def _finalizar_pdf(self):
        if not self._tifs_sessao:
            self._set_status("Nenhuma página para salvar.")
            return
        pasta = self.dest_var.get().strip()
        res   = int(self.res_var.get())
        if not pasta or not os.path.isdir(pasta):
            messagebox.showerror("Pasta inválida",
                                 "A pasta de destino não existe. Escolha outra e "
                                 "clique em \"Salvar PDF agora\".",
                                 parent=self.winfo_toplevel())
            self._set_status("Páginas mantidas. Defina a pasta e salve.", T("WARN"))
            return
        # Pergunta o nome se opção estiver marcada
        if self.perg_nome_var.get():
            sugestao = "scan_" + time.strftime("%Y%m%d_%H%M%S")
            nome_pdf = simpledialog.askstring(
                "Nome do arquivo",
                "Digite o nome do arquivo PDF\n(sem extensão):",
                initialvalue=sugestao,
                parent=self.winfo_toplevel()
            )
            if not nome_pdf or not nome_pdf.strip():
                self._set_status("Nome cancelado. Páginas mantidas.", T("WARN"))
                return
            nome_pdf = re.sub(r'[<>:"/\\|?*]', "_", nome_pdf.strip())
            # Remove .pdf se o usuário digitou com extensão
            if nome_pdf.lower().endswith(".pdf"):
                nome_pdf = nome_pdf[:-4]
        else:
            nome_pdf = "scan_" + time.strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join(pasta, nome_pdf + ".pdf")
        # Se já existe, pede confirmação
        if os.path.exists(pdf_path):
            if not messagebox.askyesno(
                    "Arquivo existente",
                    "O arquivo " + nome_pdf + ".pdf já existe.\nSobrescrever?",
                    parent=self.winfo_toplevel()):
                self._set_status("Salvamento cancelado. Páginas mantidas.", T("WARN"))
                return
        try:
            tifs_para_pdf(self._tifs_sessao, pdf_path, resolucao=res)
        except Exception as e:
            messagebox.showerror("Erro ao salvar PDF", str(e), parent=self.winfo_toplevel())
            self._set_status("Falha ao salvar. Páginas mantidas.", T("ERR"))
            self.log_cb("Falha ao salvar scan: " + str(e), "err")
            return
        nome_exib = os.path.basename(pdf_path)
        self._limpar_sessao()
        self._set_status("Salvo: " + nome_exib, T("OK"))
        self.log_cb("Scan salvo: " + pdf_path, "ok")
