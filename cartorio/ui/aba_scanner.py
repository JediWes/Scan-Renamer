"""Aba de digitalizacao."""
import os
import re
import shutil
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from .. import historico
from ..config import carregar_presets, salvar_presets, PRESET_ULTIMO
from ..constantes import TIPOS
from ..scanner import (MODOS_COR_LABEL, pagina_em_branco, scanner_listar_dispositivos,
                       scanner_uma_pagina, tifs_para_pdf)
from ..tema import T, FONT_SM, FONT_XS
from . import anim
from .widgets import BarraAtividade, Botao, CampoTexto

PRESET_MANUAL = "-- manual --"

# Rotulos exibidos para os modos de cor (chaves gravadas nos presets)
COR_ROTULO = {"Colorido": "Colorido", "Cinza": "Tons de cinza", "PretoBranco": "Preto e branco"}
COR_CHAVE = {v: k for k, v in COR_ROTULO.items()}

# Destino do PDF: pasta livre ou pasta de uma declaracao (nome imageNNNNNN)
DESTINO_PASTA = "Pasta escolhida"
DESTINO_ROTULO = {t: f"Declaração de {t}" for t in TIPOS}
DESTINO_TIPO = {v: k for k, v in DESTINO_ROTULO.items()}


class AbaScanner(tk.Frame):
    RESOLUCOES = ["100", "150", "200", "300", "400", "600"]

    def __init__(self, parent, log_callback, obter_aba=None, notificar=None):
        """obter_aba(tipo) devolve a AbaDeclaracao do tipo, para salvar como imageNNNNNN."""
        super().__init__(parent, bg=T("BG"))
        self.log_cb        = log_callback
        self.notificar     = notificar or (lambda *a, **k: None)
        self._obter_aba    = obter_aba or (lambda tipo: None)
        self._presets      = carregar_presets()
        self._dispositivos = []
        self._dev_id       = ""
        self._tifs_sessao  = []
        self._tmp_dir      = None
        self._ocupado      = False
        self._build()
        self._atualizar_menu_presets()
        self._aplicar_config(self._presets.get(PRESET_ULTIMO, {}))
        self.after(300, self._detectar_dispositivos)

    # Interface

    def _build(self):
        main = tk.Frame(self, bg=T("BG"), padx=20, pady=16)
        main.pack(fill="both", expand=True)
        left  = tk.Frame(main, bg=T("BG"))
        left.pack(side="left", fill="both", expand=True, padx=(0, 20))
        right = tk.Frame(main, bg=T("BG"), width=260)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # Scanner detectado
        self._sec(left, "SCANNER")
        dev_row = tk.Frame(left, bg=T("BG"))
        dev_row.pack(fill="x", pady=(4, 12))
        self.dev_var = tk.StringVar(value="Detectando…")
        self._dev_lbl = tk.Label(dev_row, textvariable=self.dev_var,
                                 font=FONT_SM, bg=T("CARD"), fg=T("SUBTEXT"),
                                 padx=10, pady=6, anchor="w")
        self._dev_lbl.pack(side="left", fill="x", expand=True, padx=(0, 8))
        Botao(dev_row, "Detectar novamente", self._detectar_dispositivos, variante="secundario",
              dica="Procura de novo scanners conectados").pack(side="right")

        self._sep(left)

        # Presets
        self._sec(left, "PRESET")
        pr = tk.Frame(left, bg=T("BG"))
        pr.pack(fill="x", pady=(4, 12))
        self.preset_var = tk.StringVar(value=PRESET_MANUAL)
        self._preset_cb = ttk.Combobox(pr, textvariable=self.preset_var, state="readonly",
                                       font=FONT_SM)
        self._preset_cb.bind("<<ComboboxSelected>>",
                             lambda e: self._carregar_preset(self.preset_var.get()))
        self._preset_cb.pack(side="left", fill="x", expand=True, padx=(0, 6))
        Botao(pr, "Salvar", self._salvar_preset, variante="secundario",
              dica="Guarda as opções atuais com um nome").pack(side="left", padx=(0, 4))
        Botao(pr, "Excluir", self._excluir_preset, variante="secundario",
              dica="Remove o preset selecionado").pack(side="left")

        self._sep(left)

        # Configuracoes
        self._sec(left, "DIGITALIZAÇÃO")
        grid = tk.Frame(left, bg=T("BG"))
        grid.pack(fill="x", pady=(6, 0))
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(3, weight=1)

        def lbl(txt, row, col):
            tk.Label(grid, text=txt, font=FONT_XS, bg=T("BG"), fg=T("MUTED"),
                     anchor="w").grid(row=row, column=col, sticky="w", padx=(0, 8), pady=5)

        lbl("Resolução (DPI)", 0, 0)
        self.res_var = tk.StringVar(value="300")
        ttk.Combobox(grid, textvariable=self.res_var, values=self.RESOLUCOES,
                     state="readonly", width=8, font=FONT_SM
                     ).grid(row=0, column=1, sticky="ew", pady=5, padx=(0, 16))
        lbl("Modo de cor", 0, 2)
        self.cor_var = tk.StringVar(value=COR_ROTULO["Colorido"])
        ttk.Combobox(grid, textvariable=self.cor_var, values=list(COR_ROTULO.values()),
                     state="readonly", width=14, font=FONT_SM
                     ).grid(row=0, column=3, sticky="ew", pady=5)

        opcoes = tk.Frame(left, bg=T("BG"))
        opcoes.pack(fill="x", pady=(6, 0))
        opcoes.columnconfigure(0, weight=1)
        opcoes.columnconfigure(1, weight=1)
        self.duplex_var    = tk.BooleanVar(value=False)
        self.branco_var    = tk.BooleanVar(value=True)
        self.multipag_var  = tk.BooleanVar(value=False)
        self.perg_nome_var = tk.BooleanVar(value=False)
        self._check(opcoes, "Frente e verso", self.duplex_var, 0, 0,
                    comando=self._atualizar_opcoes)
        self._chk_branco = self._check(opcoes, "Remover versos em branco", self.branco_var, 1, 0)
        self._check(opcoes, "Várias páginas por documento", self.multipag_var, 0, 1)
        self._chk_nome = self._check(opcoes, "Perguntar o nome do arquivo", self.perg_nome_var, 1, 1)

        self._sep(left, topo=14)

        # Destino
        self._sec(left, "SALVAR EM")
        self.destino_var = tk.StringVar(value=DESTINO_PASTA)
        ttk.Combobox(left, textvariable=self.destino_var, state="readonly", font=FONT_SM,
                     values=[DESTINO_PASTA] + list(DESTINO_ROTULO.values())
                     ).pack(fill="x", pady=(4, 8))
        self.destino_var.trace_add("write", lambda *_: self._atualizar_opcoes())

        self._dest_pasta = tk.Frame(left, bg=T("BG"))
        self.dest_var = tk.StringVar(value="")
        CampoTexto(self._dest_pasta, self.dest_var, exemplo="Escolha onde salvar os PDFs"
                   ).pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))
        Botao(self._dest_pasta, "Procurar", self._escolher_pasta).pack(side="right")

        self._dest_info = tk.Label(left, text="", font=FONT_SM, bg=T("CARD"),
                                   fg=T("SUBTEXT"), anchor="w", justify="left",
                                   padx=10, pady=8, wraplength=520)

        # Coluna direita: botao + status
        tk.Frame(right, bg=T("BG"), height=20).pack()
        self._btn_scan = Botao(right, "Digitalizar", self._iniciar_sessao, tamanho="xl",
                               largura=220, dica="Digitaliza a folha inserida no scanner  (F7)")
        self._btn_scan.pack(fill="x", padx=10, pady=(0, 0))
        tk.Label(right, text="F7", font=FONT_XS, bg=T("BG"), fg=T("MUTED")).pack(pady=(4, 0))
        self._atividade = BarraAtividade(right)
        self._atividade.pack(fill="x", padx=10, pady=(6, 10))

        status_frame = tk.Frame(right, bg=T("CARD"),
                                highlightbackground=T("BORDER"), highlightthickness=1)
        status_frame.pack(fill="x", padx=10, pady=(0, 8))
        self._dot = tk.Frame(status_frame, bg=T("MUTED"), width=4)
        self._dot.pack(side="left", fill="y")
        self._status_var = tk.StringVar(value="Aguardando…")
        tk.Label(status_frame, textvariable=self._status_var,
                 font=FONT_XS, bg=T("CARD"), fg=T("SUBTEXT"),
                 wraplength=200, justify="left", padx=8, pady=8).pack(side="left")

        self._pags_var = tk.StringVar(value="")
        self._lbl_pags = tk.Label(right, textvariable=self._pags_var,
                 font=("Consolas", 9, "bold"),
                 bg=T("BG"), fg=T("OK"))
        self._lbl_pags.pack(padx=10, anchor="w")

        # Acoes da sessao: concluir ou descartar paginas acumuladas
        acoes = tk.Frame(right, bg=T("BG"))
        acoes.pack(fill="x", padx=10, pady=(8, 0))
        self._btn_concluir = Botao(acoes, "Salvar PDF agora", self._finalizar_pdf,
                                   dica="Gera o PDF com as páginas acumuladas")
        self._btn_concluir.pack(fill="x", pady=(0, 4))
        self._btn_descartar = Botao(acoes, "Descartar páginas", self._descartar_sessao,
                                    variante="secundario")
        self._btn_descartar.pack(fill="x")
        self._atualizar_botoes_sessao()
        self._atualizar_opcoes()

    def _check(self, pai, texto, var, linha, coluna, comando=None):
        c = tk.Checkbutton(pai, variable=var, text=texto, font=FONT_SM,
                           bg=T("BG"), fg=T("TEXT"), selectcolor=T("ENTRY_BG"),
                           activebackground=T("BG"), activeforeground=T("TEXT"),
                           disabledforeground=T("MUTED"),
                           highlightthickness=0, bd=0, command=comando)
        c.grid(row=linha, column=coluna, sticky="w", pady=4)
        return c

    def _sec(self, p, t):
        tk.Label(p, text=t, font=("Segoe UI", 8, "bold"),
                 bg=T("BG"), fg=T("MUTED"), anchor="w").pack(fill="x", pady=(0, 2))

    def _sep(self, p, topo=0):
        tk.Frame(p, bg=T("SEP"), height=1).pack(fill="x", pady=(topo, 12))

    # Destino

    def _tipo_destino(self):
        return DESTINO_TIPO.get(self.destino_var.get())

    def _atualizar_opcoes(self):
        """Habilita opcoes conforme o contexto e mostra o destino escolhido."""
        self._chk_branco.configure(state="normal" if self.duplex_var.get() else "disabled")
        tipo = self._tipo_destino()
        self._chk_nome.configure(state="disabled" if tipo else "normal")
        if tipo:
            self._dest_pasta.pack_forget()
            self._dest_info.pack(fill="x")
            self.atualizar_info_destino()
        else:
            self._dest_info.pack_forget()
            self._dest_pasta.pack(fill="x", pady=(0, 0))

    def atualizar_info_destino(self):
        tipo = self._tipo_destino()
        if not tipo:
            return
        aba = self._obter_aba(tipo)
        pasta = aba.pasta_valida() if aba else None
        if not pasta:
            self._dest_info.configure(
                fg=T("WARN"),
                text=f"A pasta de {tipo} não está configurada. "
                     f"Defina-a na aba Renomeador antes de digitalizar.")
        else:
            self._dest_info.configure(
                fg=T("SUBTEXT"),
                text=f"Pasta: {pasta}\nPróximo arquivo: {aba.previsao_proximo('.pdf')}")

    def _escolher_pasta(self):
        p = filedialog.askdirectory(title="Pasta de destino para os scans",
                                    initialdir=self.dest_var.get() or None,
                                    parent=self.winfo_toplevel())
        if p:
            self.dest_var.set(os.path.normpath(p))
            self._salvar_ultimo()

    def _pasta_destino(self):
        """Pasta onde o PDF sera salvo, ou None se invalida."""
        tipo = self._tipo_destino()
        if tipo:
            aba = self._obter_aba(tipo)
            return aba.pasta_valida() if aba else None
        p = self.dest_var.get().strip()
        return p if p and os.path.isdir(p) else None

    # Dispositivo

    def _detectar_dispositivos(self):
        self.dev_var.set("Detectando…")
        self._btn_scan.configure(state="disabled")

        def _busca():
            devs = scanner_listar_dispositivos()

            def _ui():
                if not self.winfo_exists():
                    return
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
                    if not self._ocupado:
                        self._btn_scan.configure(state="normal")
                else:
                    self.dev_var.set("Nenhum scanner encontrado")
                    self._dev_lbl.configure(fg=T("ERR"))
                    self._dot.configure(bg=T("DANGER"))
                    self._dev_id = ""
            try:
                self.after(0, _ui)
            except RuntimeError:
                pass
        threading.Thread(target=_busca, daemon=True).start()

    # Presets

    def _atualizar_menu_presets(self):
        nomes = sorted(k for k in self._presets if k != PRESET_ULTIMO)
        self._preset_cb.configure(values=[PRESET_MANUAL] + nomes)

    def _config_atual(self):
        return {
            "resolucao":  int(self.res_var.get()),
            "cor":        COR_CHAVE.get(self.cor_var.get(), "Colorido"),
            "duplex":     self.duplex_var.get(),
            "remover_branco": self.branco_var.get(),
            "multipag":   self.multipag_var.get(),
            "perg_nome":  self.perg_nome_var.get(),
            "destino":    self._tipo_destino() or "",
            "pasta":      self.dest_var.get().strip(),
        }

    def _aplicar_config(self, p):
        if not p:
            return
        res = str(p.get("resolucao", "300"))
        self.res_var.set(res if res in self.RESOLUCOES else "300")
        cor = p.get("cor", "Colorido")
        self.cor_var.set(COR_ROTULO.get(cor, COR_ROTULO["Colorido"]))
        self.duplex_var.set(bool(p.get("duplex", False)))
        self.branco_var.set(bool(p.get("remover_branco", True)))
        self.multipag_var.set(bool(p.get("multipag", False)))
        self.perg_nome_var.set(bool(p.get("perg_nome", False)))
        destino = p.get("destino", "")
        self.destino_var.set(DESTINO_ROTULO.get(destino, DESTINO_PASTA))
        pasta = p.get("pasta", "")
        if pasta:
            self.dest_var.set(pasta)
        self._atualizar_opcoes()

    def _salvar_ultimo(self):
        self._presets[PRESET_ULTIMO] = self._config_atual()
        salvar_presets(self._presets)

    def _carregar_preset(self, nome):
        if nome == PRESET_MANUAL or nome not in self._presets:
            return
        self.preset_var.set(nome)
        self._aplicar_config(self._presets[nome])
        if not self._pasta_destino():
            self._set_status("Pasta de destino do preset não encontrada.", T("WARN"))
        else:
            self._set_status("Preset carregado: " + nome)

    def _salvar_preset(self):
        atual = self.preset_var.get()
        nome = simpledialog.askstring("Salvar preset", "Nome do preset:",
                                      initialvalue=atual if atual != PRESET_MANUAL else "",
                                      parent=self.winfo_toplevel())
        if not nome or not nome.strip():
            return
        nome = nome.strip()
        if nome in (PRESET_ULTIMO, PRESET_MANUAL):
            return
        if not self._tipo_destino() and not self.dest_var.get().strip():
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
        self.notificar("Preset salvo", nome, "ok")

    def _excluir_preset(self):
        nome = self.preset_var.get()
        if nome == PRESET_MANUAL or nome not in self._presets:
            return
        if not messagebox.askyesno("Excluir", "Excluir o preset " + nome + "?",
                                   parent=self.winfo_toplevel()):
            return
        del self._presets[nome]
        salvar_presets(self._presets)
        self._atualizar_menu_presets()
        self.preset_var.set(PRESET_MANUAL)
        self._set_status("Preset excluído.")

    # Sessao de digitalizacao

    def _set_status(self, txt, cor=None):
        self._status_var.set(txt)
        if cor:
            anim.animar_cor(self._dot, "bg", cor, 250, chave="status")

    def _limpar_sessao(self):
        self._tifs_sessao = []
        if self._tmp_dir and os.path.isdir(self._tmp_dir):
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
        self._tmp_dir = None
        self._pags_var.set("")
        self._atualizar_botoes_sessao()

    def _atualizar_botoes_sessao(self):
        ativo = bool(self._tifs_sessao) and not self._ocupado
        self._btn_concluir.configure(state="normal" if ativo else "disabled")
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
        self.notificar("Páginas descartadas", tipo="aviso")

    def digitalizar(self):
        """Atalho F7: inicia a digitalizacao se o scanner estiver pronto."""
        if str(self._btn_scan["state"]) == "normal" and not self._ocupado:
            self._iniciar_sessao()

    def _iniciar_sessao(self):
        if not self._pasta_destino():
            tipo = self._tipo_destino()
            msg = (f"Configure a pasta de {tipo} na aba Renomeador antes de digitalizar."
                   if tipo else "Selecione uma pasta de destino existente antes de digitalizar.")
            self.notificar("Pasta de destino inválida", msg, "erro")
            return
        self._salvar_ultimo()
        if self._tmp_dir is None:
            self._tmp_dir = tempfile.mkdtemp(prefix="scan_")
            self._tifs_sessao = []
        self._ocupado = True
        self._btn_scan.configure(state="disabled")
        self._atualizar_botoes_sessao()
        self._set_status("Digitalizando…", T("WARN"))
        self._atividade.iniciar()
        self.update_idletasks()
        modo_cor  = MODOS_COR_LABEL.get(COR_CHAVE.get(self.cor_var.get(), "Colorido"), "cor")
        res       = int(self.res_var.get())
        duplex    = self.duplex_var.get()
        remover   = duplex and self.branco_var.get()
        multipag  = self.multipag_var.get()
        device_id = self._dev_id
        tmp_dir   = self._tmp_dir
        nome_arq  = "pag_" + str(len(self._tifs_sessao) + 1).zfill(3)

        def _run():
            try:
                novos = scanner_uma_pagina(
                    tmp_dir      = tmp_dir,
                    nome_arquivo = nome_arq,
                    resolucao    = res,
                    modo_cor     = modo_cor,
                    duplex       = duplex,
                    device_id    = device_id,
                )
                removidas = 0
                if remover:
                    # Frente e verso: o driver entrega frente, verso. Apenas versos sao avaliados.
                    mantidas = []
                    for i, p in enumerate(novos):
                        try:
                            vazio = i % 2 == 1 and pagina_em_branco(p)
                        except Exception:
                            vazio = False
                        if vazio:
                            removidas += 1
                            try:
                                os.remove(p)
                            except OSError:
                                pass
                        else:
                            mantidas.append(p)
                    novos = mantidas
                self.after(0, lambda: self._pos_scan(novos, removidas, multipag))
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self._erro_scan(msg))
        threading.Thread(target=_run, daemon=True).start()

    def _pos_scan(self, novos, removidas, multipag):
        self._ocupado = False
        self._atividade.parar()
        self._tifs_sessao.extend(novos)
        n = len(self._tifs_sessao)
        self._pags_var.set(f"{n} página(s) acumulada(s)" if n else "")
        if n:
            anim.realcar(self._lbl_pags, "fg", T("TEXT"), T("OK"), 700)
        self._btn_scan.configure(state="normal")
        self._atualizar_botoes_sessao()
        if removidas:
            self.log_cb(f"{removidas} verso(s) em branco removido(s).", "info")
            self.notificar("Verso em branco removido",
                           f"{removidas} página(s) vazia(s) não entraram no PDF.", "info")
        if not n:
            self._set_status("Nenhuma página com conteúdo.", T("WARN"))
            return
        if multipag:
            msg = (f"{n} página(s) acumulada(s).\n\n"
                   "Sim: escanear a próxima página\n"
                   "Não: salvar o PDF agora")
            if messagebox.askyesno("Continuar?", msg, parent=self.winfo_toplevel()):
                self._set_status("Escaneando a próxima página…", T("WARN"))
                self._iniciar_sessao()
            else:
                self._finalizar_pdf()
        else:
            self._finalizar_pdf()

    def _erro_scan(self, msg):
        self._ocupado = False
        self._atividade.parar()
        self._btn_scan.configure(state="normal")
        self._atualizar_botoes_sessao()
        self._set_status("Erro: " + msg[:60], T("DANGER"))
        self.notificar("Falha ao digitalizar", msg, "erro", duracao_ms=8000)
        self.log_cb("Falha ao digitalizar: " + msg, "err")

    def _caminho_pasta_livre(self, pasta):
        """Nome do PDF na pasta escolhida. Retorna None se o usuario cancelar."""
        sugestao = "scan_" + time.strftime("%Y%m%d_%H%M%S")
        if self.perg_nome_var.get():
            nome_pdf = simpledialog.askstring(
                "Nome do arquivo", "Digite o nome do arquivo PDF\n(sem extensão):",
                initialvalue=sugestao, parent=self.winfo_toplevel())
            if not nome_pdf or not nome_pdf.strip():
                self._set_status("Nome cancelado. Páginas mantidas.", T("WARN"))
                return None
            nome_pdf = re.sub(r'[<>:"/\\|?*]', "_", nome_pdf.strip())
            if nome_pdf.lower().endswith(".pdf"):
                nome_pdf = nome_pdf[:-4]
        else:
            nome_pdf = sugestao
        caminho = os.path.join(pasta, nome_pdf + ".pdf")
        if os.path.exists(caminho) and not messagebox.askyesno(
                "Arquivo existente",
                f"O arquivo {nome_pdf}.pdf já existe.\nSobrescrever?",
                parent=self.winfo_toplevel()):
            self._set_status("Salvamento cancelado. Páginas mantidas.", T("WARN"))
            return None
        return caminho

    def _finalizar_pdf(self):
        if not self._tifs_sessao:
            self._set_status("Nenhuma página para salvar.")
            return
        pasta = self._pasta_destino()
        if not pasta:
            messagebox.showerror("Pasta inválida",
                                 "A pasta de destino não existe. Corrija e clique em "
                                 "\"Salvar PDF agora\".", parent=self.winfo_toplevel())
            self._set_status("Páginas mantidas. Defina a pasta e salve.", T("WARN"))
            return
        res  = int(self.res_var.get())
        tipo = self._tipo_destino()
        aba  = self._obter_aba(tipo) if tipo else None
        numero = None
        if aba:
            pdf_path, numero = aba.reservar_numero(".pdf")
        else:
            pdf_path = self._caminho_pasta_livre(pasta)
            if not pdf_path:
                return
        try:
            tifs_para_pdf(self._tifs_sessao, pdf_path, resolucao=res)
        except Exception as e:
            if aba:
                aba.devolver_numero(numero)
            messagebox.showerror("Erro ao salvar PDF", str(e), parent=self.winfo_toplevel())
            self._set_status("Falha ao salvar. Páginas mantidas.", T("ERR"))
            self.log_cb("Falha ao salvar scan: " + str(e), "err")
            return
        n_pag = len(self._tifs_sessao)
        nome_exib = os.path.basename(pdf_path)
        historico.registrar(historico.SCANNER, tipo or "", pasta, f"{n_pag} página(s)", nome_exib)
        self._limpar_sessao()
        self._set_status("Salvo: " + nome_exib, T("OK"))
        self.notificar("PDF salvo", f"{nome_exib}  ·  {n_pag} página(s)", "ok")
        if aba:
            aba.registrar_scan(pdf_path)
            self.atualizar_info_destino()
        else:
            self.log_cb("Scan salvo: " + pdf_path, "ok")
