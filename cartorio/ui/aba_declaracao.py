"""Aba de cada tipo de declaracao (Nascimento, Obito, Natimorto)."""
import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from ..tema import T, FONT, FONT_SM, FONT_XS

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

    def __init__(self, parent, tipo, app_log, get_prefs):
        super().__init__(parent, bg=T("PANEL"))
        self.tipo = tipo; self.app_log = app_log; self.get_prefs = get_prefs
        self.observer = None; self.monitorando = False
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
        left.pack(side="left", fill="both", expand=True, padx=(0, 14))

        self._lbl(left, "PASTA DE DESTINO")
        rp = tk.Frame(left, bg=T("PANEL"))
        rp.pack(fill="x", pady=(4, 4))
        tk.Entry(rp, textvariable=self.pasta_var, font=FONT,
                 bg=T("ENTRY_BG"), fg=T("TEXT"), insertbackground=T("TEXT"),
                 relief="flat", bd=0,
                 highlightbackground=T("BORDER"), highlightthickness=1
                 ).pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 8))
        tk.Button(rp, text="Procurar", font=FONT_SM,
                  bg=T("ACCENT"), fg=T("TEXT_ON_ACCENT"), relief="flat", cursor="hand2",
                  padx=10, pady=6, bd=0,
                  activebackground=T("ACCENT2"), activeforeground=T("TEXT_ON_ACCENT"),
                  command=self._escolher_pasta).pack(side="right")

        cr = tk.Frame(left, bg=T("PANEL"))
        cr.pack(fill="x", pady=(2, 12))
        tk.Label(cr, text="Arquivos na pasta:", font=FONT_XS,
                 bg=T("PANEL"), fg=T("MUTED")).pack(side="left")
        tk.Label(cr, textvariable=self.count_var, font=("Consolas", 9, "bold"),
                 bg=T("PANEL"), fg=T("OK")).pack(side="left", padx=5)
        tk.Button(cr, text="Atualizar", font=FONT_XS,
                  bg=T("PANEL"), fg=T("MUTED"), relief="flat", cursor="hand2",
                  bd=0, padx=3,
                  activebackground=T("CARD"), activeforeground=T("TEXT"),
                  command=self._atualizar_contador_pasta).pack(side="left")
        tk.Button(cr, text="Lote", font=FONT_XS,
                  bg=T("BTN_SEC_BG"), fg=T("BTN_SEC_FG"), relief="flat", cursor="hand2",
                  padx=8, pady=2, bd=0,
                  activebackground=T("ACCENT"), activeforeground=T("TEXT_ON_ACCENT"),
                  command=self._abrir_lote).pack(side="right")

        tk.Frame(left, bg=T("SEP"), height=1).pack(fill="x", pady=(0, 12))

        self._lbl(left, "PRÓXIMO A SER ESCANEADO")
        rn = tk.Frame(left, bg=T("PANEL"))
        rn.pack(fill="x", pady=(4, 12))
        tk.Entry(rn, textvariable=self.num_var,
                 font=("Consolas", 13, "bold"),
                 bg=T("ENTRY_BG"), fg=T("OK"), insertbackground=T("OK"),
                 relief="flat", bd=0,
                 highlightbackground=T("BORDER"), highlightthickness=1,
                 width=15).pack(side="left", ipady=8, padx=(0, 8))
        tk.Button(rn, text="Verificar", font=FONT_SM,
                  bg=T("ACCENT"), fg=T("TEXT_ON_ACCENT"), relief="flat", cursor="hand2",
                  padx=10, pady=6, bd=0,
                  activebackground=T("ACCENT2"), activeforeground=T("TEXT_ON_ACCENT"),
                  command=self._verificar_numeracao).pack(side="left")
        tk.Label(rn, text="image+6 dígitos", font=FONT_XS,
                 bg=T("PANEL"), fg=T("MUTED")).pack(side="left", padx=10)

        tk.Frame(left, bg=T("SEP"), height=1).pack(fill="x", pady=(0, 12))

        self.btn_var = tk.StringVar(value="Iniciar  [F5]")
        self.btn = tk.Button(left, textvariable=self.btn_var,
                             font=("Segoe UI", 11, "bold"),
                             bg=T("SUCCESS"), fg=T("TEXT_ON_ACCENT"),
                             relief="flat", cursor="hand2",
                             padx=20, pady=12, bd=0,
                             activebackground=T("DANGER"), activeforeground=T("TEXT_ON_ACCENT"),
                             command=self._toggle)
        self.btn.pack(fill="x", pady=(0, 8))

        self.lbl_notif = tk.Label(left, text="", font=("Segoe UI", 9, "bold"),
                                   bg=T("NOTIF_BG"), fg=T("NOTIF_FG"),
                                   anchor="center", pady=4)

        bar = tk.Frame(left, bg=T("CARD"),
                       highlightbackground=T("BORDER"), highlightthickness=1)
        bar.pack(fill="x")
        self._dot = tk.Frame(bar, bg=T("MUTED"), width=4)
        self._dot.pack(side="left", fill="y")
        tk.Label(bar, text="STATUS", font=("Segoe UI", 7, "bold"),
                 bg=T("CARD"), fg=T("MUTED")).pack(side="left", padx=(10, 6), pady=7)
        self.lbl_status = tk.Label(bar, text="Aguardando…",
                                   font=FONT_SM, bg=T("CARD"), fg=T("SUBTEXT"))
        self.lbl_status.pack(side="left")
        self.lbl_counter = tk.Label(bar, text="",
                                    font=("Consolas", 9, "bold"),
                                    bg=T("CARD"), fg=T("OK"))
        self.lbl_counter.pack(side="right", padx=10)

        # Direita — preview
        right = tk.Frame(root, bg=T("CARD2"),
                         highlightbackground=T("BORDER"), highlightthickness=1,
                         width=self.PW)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        tk.Label(right, text="ÚLTIMO ESCANEADO", font=("Segoe UI", 7, "bold"),
                 bg=T("CARD2"), fg=T("MUTED")).pack(pady=(10, 4))
        self._pcv = tk.Canvas(right, width=self.PW-20, height=self.PH,
                               bg=T("CARD"), highlightthickness=0, cursor="hand2")
        self._pcv.pack(padx=10)
        self._pcv.bind("<Button-1>", self._abrir_visualizacao)
        self._prev_ref = None
        self._placeholder()
        self.lbl_pnome = tk.Label(right, text="—", font=("Consolas", 8),
                                   bg=T("CARD2"), fg=T("MUTED"),
                                   wraplength=self.PW-16, justify="center")
        self.lbl_pnome.pack(pady=(6, 4), padx=6)
        tk.Button(right, text="Ver tamanho real", font=FONT_XS,
                  bg=T("ACCENT"), fg=T("TEXT_ON_ACCENT"), relief="flat", cursor="hand2",
                  padx=8, pady=5, bd=0,
                  activebackground=T("ACCENT2"), activeforeground=T("TEXT_ON_ACCENT"),
                  command=self._abrir_visualizacao_btn).pack(fill="x", padx=10, pady=(4, 3))
        tk.Button(right, text="Abrir pasta no Explorer", font=FONT_XS,
                  bg=T("BTN_SEC_BG"), fg=T("BTN_SEC_FG"), relief="flat", cursor="hand2",
                  padx=8, pady=5, bd=0,
                  activebackground=T("ACCENT"), activeforeground=T("TEXT_ON_ACCENT"),
                  command=self._abrir_pasta).pack(fill="x", padx=10, pady=(0, 10))

    def _lbl(self, p, t):
        tk.Label(p, text=t, font=("Segoe UI", 8, "bold"),
                 bg=T("PANEL"), fg=T("MUTED"), anchor="w").pack(fill="x", pady=(0, 2))

    def _placeholder(self):
        W, H = self.PW-20, self.PH
        self._pcv.delete("all")
        self._pcv.configure(bg=T("CARD"))
        self._pcv.create_rectangle(0, 0, W, H, fill=T("CARD"), outline="")
        self._pcv.create_text(W//2, H//2-10, text="Sem prévia", font=("Segoe UI", 10), fill=T("MUTED"))
        self._pcv.create_text(W//2, H//2+24, text="aguardando…", font=("Segoe UI", 8), fill=T("MUTED"))

    def flash_notificacao(self, nome, caminho):
        self._ultimo_caminho = caminho
        def _show():
            self.lbl_notif.configure(text=nome)
            self.lbl_notif.pack(fill="x", pady=(0, 6))
            if self._flash_job: self.after_cancel(self._flash_job)
            self._flash_job = self.after(4000, _hide)
            self._pulsar_btn(3)
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
        self._pcv.create_text(W//2, H//2-14, text="Sem prévia", font=("Segoe UI", 10), fill=T("MUTED"))
        self._pcv.create_text(W//2, H//2+18, text=ext, font=("Segoe UI", 10, "bold"), fill=T("SUBTEXT"))
        self._pcv.create_text(W//2, H//2+36, text="sem visualização", font=("Segoe UI", 7), fill=T("MUTED"))

    def _abrir_pasta(self):
        p = self.pasta_var.get().strip()
        if p and os.path.isdir(p):
            os.startfile(p)
        else:
            messagebox.showwarning("Pasta inválida", "Configure a pasta primeiro.", parent=self)

    def _abrir_visualizacao(self, event=None):
        if self._ultimo_caminho and os.path.exists(self._ultimo_caminho):
            JanelaVisualizacao(self, self._ultimo_caminho)

    def _abrir_visualizacao_btn(self):
        if self._ultimo_caminho and os.path.exists(self._ultimo_caminho):
            JanelaVisualizacao(self, self._ultimo_caminho)
        else:
            messagebox.showinfo("Sem arquivo", "Nenhum arquivo escaneado ainda.", parent=self)

    def _abrir_lote(self):
        p = self.pasta_var.get().strip()
        if not p or not os.path.isdir(p):
            messagebox.showerror("Pasta inválida",
                                 "Configure a pasta antes de usar o modo lote.", parent=self)
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

    def _pulsar_btn(self, vezes):
        if vezes <= 0 or not self.monitorando: return
        self.btn.configure(bg=T("OK"), fg=T("TEXT_ON_ACCENT"))
        self.after(150, lambda: self.btn.configure(bg=T("DANGER"), fg=T("TEXT_ON_ACCENT")))
        self.after(300, lambda: self._pulsar_btn(vezes - 1))

    def _atualizar_contador_pasta(self):
        p = self.pasta_var.get().strip()
        if p and os.path.isdir(p):
            exts = set(self.get_prefs().get("extensoes", EXTENSOES_PADRAO))
            n = contar_arquivos_pasta(p, exts)
            self.count_var.set(f"{n} arquivo{'s' if n != 1 else ''}")
        else:
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
            if not silencioso: messagebox.showwarning("Pasta inválida", "Configure a pasta antes de verificar.")
            return
        prox = detectar_proximo_numero(p)
        if prox is None:
            if not silencioso: messagebox.showinfo("Nenhum arquivo", "Nenhum image000000 encontrado.\nNumeração mantida.")
            return
        self.num_var.set(f"image{prox:06d}")
        if not silencioso:
            messagebox.showinfo("Numeração detectada",
                                f"Último: image{prox-1:06d}\nPróximo: image{prox:06d}")

    def _toggle(self):
        if self.monitorando: self._parar()
        else:                self._iniciar()

    def _iniciar(self):
        p = self.pasta_var.get().strip()
        if not p or not os.path.isdir(p):
            messagebox.showerror("Pasta inválida", f"Configure a pasta de '{self.tipo}' antes de iniciar.")
            return
        m = re.fullmatch(r"image(\d{6})", self.num_var.get().strip().lower())
        if not m:
            messagebox.showerror("Numeração inválida", "Use: image + 6 dígitos\nEx: image397568")
            return
        prefs = self.get_prefs()
        self.proximo_numero = int(m.group(1)); self.total_renomeados = 0
        self.log("── Iniciando ─────────────────────────────────────", "info")
        self.log(f"   Tipo : Declaração de {self.tipo}", "info")
        self.log(f"   Pasta: {p}", "info")
        self.log(f"   A partir de: image{self.proximo_numero:06d}", "info")
        self.log("──────────────────────────────────────────────────", "info")
        handler = RenomeadorHandler(self,
            extensoes=prefs.get("extensoes", EXTENSOES_PADRAO),
            delay=prefs.get("delay", 0.3))
        self.observer = Observer()
        self.observer.schedule(handler, p, recursive=False)
        self.observer.start()
        self.monitorando = True
        self.btn_var.set("Parar  [F5]")
        self.btn.configure(bg=T("DANGER"), activebackground=T("DANGER_HOVER"))
        self._dot.configure(bg=T("OK"))
        self.lbl_status.configure(text=f"Monitorando  ·  {os.path.basename(p)}", fg=T("OK"))

    def _parar(self):
        if self.observer:
            self.observer.stop(); self.observer.join(); self.observer = None
        self.monitorando = False
        self.btn_var.set("Iniciar  [F5]")
        self.btn.configure(bg=T("SUCCESS"), activebackground=T("DANGER"))
        self._dot.configure(bg=T("MUTED"))
        self.lbl_status.configure(text="Monitoramento encerrado.", fg=T("SUBTEXT"))
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
