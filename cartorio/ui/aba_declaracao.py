"""Aba de cada tipo de declaracao (Nascimento, Obito, Natimorto)."""
import os
import re
import threading
import tkinter as tk
from tkinter import filedialog

from ..tema import T, FONT, FONT_SM, FONT_XS, F_ABA, F_MINI, F_MONO_B, F_MONO_XS, F_PEQ_B, F_SECAO, espacado
from . import anim
from .widgets import Botao, CampoTexto, Odometro

try:
    from watchdog.observers.winapi import WindowsApiObserver as Observer
except (ImportError, AttributeError, OSError):
    from watchdog.observers import Observer

from ..arquivos import detectar_proximo_numero, contar_arquivos_pasta, carregar_thumbnail
from ..config import carregar_config, salvar_config
from ..constantes import EXTENSOES_PADRAO
from ..renomeador import RenomeadorHandler
from .lote import JanelaLote
from .visualizador import JanelaVisualizacao


class AbaDeclaracao(tk.Frame):
    PW = 180; PH = 155

    def __init__(self, parent, tipo, app_log, get_prefs, notificar=None):
        super().__init__(parent, bg=T("PANEL"))
        self.tipo = tipo; self.app_log = app_log; self.get_prefs = get_prefs
        self.notificar = notificar or (lambda *a, **k: None)
        self.observer = None; self.handler = None; self.monitorando = False
        self.proximo_numero = 0; self.total_renomeados = 0
        # Protege a numeracao entre monitoramento, lote e scanner
        self.lock_numero = threading.RLock()
        self._flash_job = None; self._preview_ref = None; self._ultimo_caminho = None
        cfg = carregar_config().get(tipo, {})
        _p = cfg.get("pasta", ""); _n = cfg.get("numero", "image000001")
        if _p and not os.path.isdir(_p): _p = ""
        self.pasta_var = tk.StringVar(value=_p)
        self.num_var   = tk.StringVar(value=_n)
        self.count_var = tk.StringVar(value="—")
        self.proximo_numero = self._numero_digitado() or 0
        self._build()
        if _p and os.path.isdir(_p): self._atualizar_contador_pasta()

    def _build(self):
        root = tk.Frame(self, bg=T("PANEL"), padx=20, pady=16)
        root.pack(fill="both", expand=True)

        # Esquerda
        left = tk.Frame(root, bg=T("PANEL"))
        left.pack(side="left", fill="both", expand=True, padx=(0, 16))

        self._lbl(left, "Pasta monitorada")
        rp = tk.Frame(left, bg=T("PANEL"))
        rp.pack(fill="x", pady=(4, 4))
        CampoTexto(rp, self.pasta_var, exemplo="Escolha a pasta onde o scanner salva os arquivos",
                   font=FONT).pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        Botao(rp, "Procurar", self._escolher_pasta, dica="Escolher pasta  (Ctrl+O)").pack(side="right")

        cr = tk.Frame(left, bg=T("PANEL"))
        cr.pack(fill="x", pady=(4, 12))
        tk.Label(cr, text="Arquivos já numerados:", font=FONT_XS,
                 bg=T("PANEL"), fg=T("MUTED")).pack(side="left")
        tk.Label(cr, textvariable=self.count_var, font=F_MONO_B,
                 bg=T("PANEL"), fg=T("OK")).pack(side="left", padx=5)
        Botao(cr, "Atualizar", self._atualizar_contador_pasta, variante="fantasma", tamanho="sm",
              dica="Contar novamente os arquivos imageNNNNNN da pasta").pack(side="left")
        Botao(cr, "Renomear em lote", self._abrir_lote, variante="secundario", tamanho="sm",
              dica="Renomeia de uma vez os arquivos da pasta que ainda não seguem o padrão"
              ).pack(side="right")

        tk.Frame(left, bg=T("SEP"), height=1).pack(fill="x", pady=(0, 12))

        self._lbl(left, "Próximo número")
        rn = tk.Frame(left, bg=T("PANEL"))
        rn.pack(fill="x", pady=(4, 12))
        self._num_entry = Odometro(rn, self.num_var,
                                   validar=lambda v: re.fullmatch(r"image\d{6}", v) is not None,
                                   dica="Clique para editar. Enter confirma, Esc cancela.")
        self._num_entry.pack(side="left", padx=(0, 10))
        Botao(rn, "Detectar", self._verificar_numeracao, variante="secundario",
              dica="Procura o maior imageNNNNNN da pasta e sugere o seguinte  (F2)").pack(side="left")
        tk.Label(rn, text="formato: image + 6 dígitos", font=FONT_XS,
                 bg=T("PANEL"), fg=T("MUTED")).pack(side="left", padx=12)

        tk.Frame(left, bg=T("SEP"), height=1).pack(fill="x", pady=(0, 12))

        self.btn_var = tk.StringVar(value="Iniciar monitoramento  [F5]")
        self.btn = Botao(left, comando=self._toggle, tamanho="lg", textvariable=self.btn_var,
                         largura=200)
        self.btn.pack(fill="x", pady=(0, 8))

        self.lbl_notif = tk.Label(left, text="", font=F_PEQ_B,
                                  bg=T("NOTIF_BG"), fg=T("NOTIF_FG"),
                                  anchor="center", pady=5)

        bar = tk.Frame(left, bg=T("CARD"),
                       highlightbackground=T("BORDER"), highlightthickness=1)
        bar.pack(fill="x")
        self._dot = tk.Frame(bar, bg=T("MUTED"), width=4)
        self._dot.pack(side="left", fill="y")
        self._resp = anim.Respiracao(self._dot, "bg", T("OK"), anim.misturar(T("OK"), T("CARD"), 0.75))
        tk.Label(bar, text=espacado("STATUS"), font=F_MINI,
                 bg=T("CARD"), fg=T("MUTED")).pack(side="left", padx=(10, 6), pady=7)
        self.lbl_status = tk.Label(bar, text="Parado", font=FONT_SM, bg=T("CARD"), fg=T("SUBTEXT"))
        self.lbl_status.pack(side="left")
        self.lbl_counter = tk.Label(bar, text="", font=F_MONO_B,
                                    bg=T("CARD"), fg=T("OK"))
        self.lbl_counter.pack(side="right", padx=10)

        # Direita: ultimo arquivo
        right = tk.Frame(root, bg=T("CARD2"),
                         highlightbackground=T("BORDER"), highlightthickness=1,
                         width=self.PW)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        tk.Label(right, text=espacado("ÚLTIMO ARQUIVO"), font=F_MINI,
                 bg=T("CARD2"), fg=T("MUTED")).pack(pady=(10, 4))
        self._pcv = tk.Canvas(right, width=self.PW-20, height=self.PH,
                              bg=T("CARD"), highlightthickness=0, cursor="hand2")
        self._pcv.pack(padx=10)
        self._pcv.bind("<Button-1>", self._abrir_visualizacao)
        self._prev_ref = None
        self._placeholder()
        self.lbl_pnome = tk.Label(right, text="—", font=F_MONO_XS,
                                  bg=T("CARD2"), fg=T("MUTED"),
                                  wraplength=self.PW-16, justify="center")
        self.lbl_pnome.pack(pady=(6, 4), padx=6)
        Botao(right, "Ampliar", self._abrir_visualizacao_btn, tamanho="sm",
              dica="Abrir o último arquivo em tamanho real").pack(fill="x", padx=10, pady=(4, 4))
        Botao(right, "Abrir pasta", self._abrir_pasta, variante="secundario", tamanho="sm",
              dica="Abrir a pasta no Explorer").pack(fill="x", padx=10, pady=(0, 10))

    def ao_exibir(self):
        """Chamado quando a aba fica visivel."""
        if self.pasta_valida():
            self._atualizar_contador_pasta()

    def _visual_monitorando(self, ativo):
        if ativo:
            self.btn_var.set("Parar monitoramento  [F5]")
            self.btn.configure(variante="perigo")
            self._resp.iniciar()
            p = self.pasta_var.get().strip()
            anim.trocar_texto(self.lbl_status, f"Monitorando  ·  {os.path.basename(p) or p}", T("OK"))
        else:
            self.btn_var.set("Iniciar monitoramento  [F5]")
            self.btn.configure(variante="primario")
            self._resp.parar()
            anim.animar_cor(self._dot, "bg", T("MUTED"), 300)
            anim.trocar_texto(self.lbl_status, "Parado", T("SUBTEXT"))
            if self.total_renomeados:
                anim.trocar_texto(self.lbl_counter,
                                  f"{self.total_renomeados} renomeado(s) na última sessão", T("MUTED"))

    def _lbl(self, p, t):
        tk.Label(p, text=t, font=F_SECAO,
                 bg=T("PANEL"), fg=T("MUTED"), anchor="w").pack(fill="x", pady=(0, 2))

    def _placeholder(self):
        W, H = self.PW-20, self.PH
        self._pcv.delete("all")
        self._pcv.configure(bg=T("CARD"))
        self._pcv.create_rectangle(0, 0, W, H, fill=T("CARD"), outline="")
        self._pcv.create_text(W//2, H//2-10, text="Sem prévia", font=FONT, fill=T("MUTED"))
        self._pcv.create_text(W//2, H//2+24, text="aguardando…", font=FONT_XS, fill=T("MUTED"))

    def flash_notificacao(self, nome, caminho):
        self._ultimo_caminho = caminho
        def _show():
            self.lbl_notif.configure(text=nome)
            self.lbl_notif.pack(fill="x", pady=(0, 6), before=self.btn)
            anim.realcar(self.lbl_notif, "bg", T("ACCENT"), T("NOTIF_BG"), 700)
            if self._flash_job: self.after_cancel(self._flash_job)
            self._flash_job = self.after(4000, _hide)
            threading.Thread(target=self._load_preview, args=(caminho, nome), daemon=True).start()
        def _hide():
            self.lbl_notif.pack_forget(); self._flash_job = None
        self.after(0, _show)

    def _load_preview(self, caminho, nome):
        W, H = self.PW-20, self.PH
        img = carregar_thumbnail(caminho, W, H)
        def _paint():
            self._pcv.delete("all")
            self._pcv.configure(bg=T("CARD"))
            if img:
                try:
                    from PIL import ImageTk
                    photo = ImageTk.PhotoImage(img)
                    self._prev_ref = photo
                    iw, ih = img.size
                    x = (W-iw)//2; y = (H-ih)//2
                    self._pcv.create_rectangle(0, 0, W, H, fill=T("CARD"), outline="")
                    self._pcv.create_image(x, y, anchor="nw", image=photo)
                except Exception:
                    self._no_prev(W, H, nome)
            else:
                self._no_prev(W, H, nome)
            self.lbl_pnome.configure(text=nome)
        self.after(0, _paint)

    def _no_prev(self, W, H, nome):
        ext = os.path.splitext(nome)[1][1:].upper() if "." in nome else "?"
        self._pcv.create_rectangle(0, 0, W, H, fill=T("CARD"), outline="")
        self._pcv.create_text(W//2, H//2-14, text="Sem prévia", font=FONT, fill=T("MUTED"))
        self._pcv.create_text(W//2, H//2+18, text=ext, font=F_ABA, fill=T("SUBTEXT"))
        self._pcv.create_text(W//2, H//2+36, text="sem visualização", font=FONT_XS, fill=T("MUTED"))

    def _abrir_pasta(self):
        p = self.pasta_var.get().strip()
        if p and os.path.isdir(p):
            os.startfile(p)
        else:
            self.notificar("Pasta não configurada", f"Escolha a pasta de {self.tipo} primeiro.", "aviso")

    def _abrir_visualizacao(self, event=None):
        if self._ultimo_caminho and os.path.exists(self._ultimo_caminho):
            JanelaVisualizacao(self, self._ultimo_caminho)

    def _abrir_visualizacao_btn(self):
        if self._ultimo_caminho and os.path.exists(self._ultimo_caminho):
            JanelaVisualizacao(self, self._ultimo_caminho)
        else:
            self.notificar("Nenhum arquivo ainda", "O último arquivo renomeado aparece aqui.", "info")

    def _abrir_lote(self):
        p = self.pasta_var.get().strip()
        if not p or not os.path.isdir(p):
            self.notificar("Pasta não configurada", "Escolha a pasta antes de renomear em lote.", "aviso")
            return
        prefs = self.get_prefs()
        JanelaLote(self, self.tipo, p,
                   prefs.get("extensoes", EXTENSOES_PADRAO),
                   self._numero_atual(),
                   self._lote_concluido)

    def _lote_concluido(self, novo_proximo):
        self.proximo_numero = novo_proximo
        self.num_var.set(f"image{novo_proximo:06d}")
        self._atualizar_contador_pasta()
        self._persistir()

    def _atualizar_contador_pasta(self):
        p = self.pasta_var.get().strip()
        if p and os.path.isdir(p):
            exts = set(self.get_prefs().get("extensoes", EXTENSOES_PADRAO))
            n = contar_arquivos_pasta(p, exts)
            anterior = getattr(self, "_contagem", None)
            self._contagem = n
            anim.contar(self, self.count_var, anterior, n,
                        lambda k: f"{k} arquivo{'s' if k != 1 else ''}", 700)
        else:
            self._contagem = None
            self.count_var.set("—")

    def _escolher_pasta(self):
        p = filedialog.askdirectory(title=f"Selecionar pasta — Declaração de {self.tipo}")
        if not p: return
        self.pasta_var.set(os.path.normpath(p))
        self._verificar_numeracao(silencioso=True)
        self._atualizar_contador_pasta()

    def _verificar_numeracao(self, silencioso=False):
        p = self.pasta_var.get().strip()
        if not p or not os.path.isdir(p):
            if not silencioso: self.notificar("Pasta não configurada", "Escolha a pasta antes de detectar a numeração.", "aviso")
            return
        prox = detectar_proximo_numero(p)
        if prox is None:
            if not silencioso: self.notificar("Nenhum arquivo numerado", "A numeração atual foi mantida.", "info")
            return
        self.num_var.set(f"image{prox:06d}")
        if not silencioso:
            self.notificar("Numeração detectada",
                           f"Último: image{prox-1:06d}   ·   Próximo: image{prox:06d}", "ok")

    def _toggle(self):
        if self.monitorando: self._parar()
        else:                self._iniciar()

    def _iniciar(self):
        p = self.pasta_var.get().strip()
        if not p or not os.path.isdir(p):
            self.notificar("Pasta não configurada", f"Escolha a pasta de {self.tipo} antes de iniciar.", "erro")
            return
        m = re.fullmatch(r"image(\d{6})", self.num_var.get().strip().lower())
        if not m:
            self.notificar("Numeração inválida", "Use image seguido de 6 dígitos, por exemplo image397568.", "erro")
            self._num_entry.realcar(anim.misturar(T("ERR"), T("ENTRY_BG"), 0.55))
            return
        prefs = self.get_prefs()
        self.proximo_numero = int(m.group(1)); self.total_renomeados = 0
        self.log("── Iniciando ─────────────────────────────────────", "info")
        self.log(f"   Tipo : Declaração de {self.tipo}", "info")
        self.log(f"   Pasta: {p}", "info")
        self.log(f"   A partir de: image{self.proximo_numero:06d}", "info")
        self.log("──────────────────────────────────────────────────", "info")
        handler = self.handler = RenomeadorHandler(self,
            extensoes=prefs.get("extensoes", EXTENSOES_PADRAO),
            delay=prefs.get("delay", 0.3))
        self.observer = Observer()
        self.observer.schedule(handler, p, recursive=False)
        self.observer.start()
        self.monitorando = True
        self._visual_monitorando(True)
        self.notificar(f"Monitorando {self.tipo}", p, "ok")

    def _parar(self):
        if self.observer:
            self.observer.stop(); self.observer.join(); self.observer = None
        self.handler = None
        self.monitorando = False
        self._visual_monitorando(False)
        self.log("── Monitoramento encerrado ───────────────────────", "info")
        self._atualizar_contador_pasta(); self._persistir()

    def _numero_digitado(self):
        m = re.fullmatch(r"image(\d{6})", self.num_var.get().strip().lower())
        return int(m.group(1)) if m else None

    def _numero_atual(self):
        """Proximo numero: o do monitoramento se ativo, senao o digitado no campo."""
        if self.monitorando:
            return self.proximo_numero
        n = self._numero_digitado()
        return n if n is not None else self.proximo_numero

    def _persistir(self):
        salvar_config(self.tipo, self.pasta_var.get().strip(), f"image{self._numero_atual():06d}")

    # Integracao com o scanner e com o desfazer

    def pasta_valida(self):
        p = self.pasta_var.get().strip()
        return p if p and os.path.isdir(p) else None

    def previsao_proximo(self, ext=".pdf"):
        """Nome que o proximo scan recebera, sem reservar."""
        p = self.pasta_valida()
        n = self._numero_atual()
        if p:
            while os.path.exists(os.path.join(p, f"image{n:06d}{ext}")):
                n += 1
        return f"image{n:06d}{ext}"

    def reservar_numero(self, ext):
        """Reserva o proximo imageNNNNNN livre. Retorna (caminho, numero)."""
        p = self.pasta_valida()
        if not p:
            raise ValueError(f"A pasta de {self.tipo} não está configurada.")
        with self.lock_numero:
            n = self._numero_atual()
            while os.path.exists(os.path.join(p, f"image{n:06d}{ext}")):
                n += 1
            self.proximo_numero = n + 1
            self.num_var.set(f"image{n + 1:06d}")
            self._persistir()
        return os.path.join(p, f"image{n:06d}{ext}"), n

    def devolver_numero(self, n):
        """Desfaz uma reserva ou renomeacao se ela ainda for a ultima numeracao usada."""
        with self.lock_numero:
            if self._numero_atual() == n + 1:
                self.proximo_numero = n
                self.num_var.set(f"image{n:06d}")
                self._persistir()
                self.atualizar_contador()

    def registrar_scan(self, caminho):
        self.log(f"Scan salvo em {self.tipo}: {os.path.basename(caminho)}", "ok")
        self._atualizar_contador_pasta()
        self.flash_notificacao(os.path.basename(caminho), caminho)

    def log(self, msg, tag="info"): self.app_log(msg, tag)

    def atualizar_contador(self):
        def _u():
            if self.monitorando:
                self.lbl_counter.configure(
                    text=f"{self.total_renomeados} renomeados  ·  próx image{self.proximo_numero:06d}")
            self.num_var.set(f"image{self._numero_atual():06d}")
            self._atualizar_contador_pasta()
        self.after(0, _u)

    def parar_se_ativo(self):
        if self.monitorando: self._parar()
