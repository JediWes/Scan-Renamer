"""Visualizador de imagem/PDF com zoom."""
import os
import threading
import tkinter as tk
from tkinter import messagebox

from ..arquivos import pdf_para_imagem
from ..tema import T, FONT_B, FONT_XS


class JanelaVisualizacao(tk.Toplevel):
    def __init__(self, master, caminho):
        super().__init__(master)
        self.title(os.path.basename(caminho))
        self.configure(bg=T("BG"))
        self.geometry("900x700")
        self._zoom = 1.0
        self._caminho = caminho
        self._pil_img = None
        self._img_ref = None
        self._build()

    def _build(self):
        tb = tk.Frame(self, bg=T("SIDEBAR"), pady=8)
        tb.pack(fill="x")
        tk.Label(tb, text=os.path.basename(self._caminho),
                 font=FONT_B, bg=T("SIDEBAR"), fg=T("TEXT")
                 ).pack(side="left", padx=14)
        for txt, cmd in [("Zoom +", self._zoom_in),
                          ("Zoom −", self._zoom_out),
                          ("Ajustar", self._zoom_fit),
                          ("1:1  Original", self._zoom_real)]:
            tk.Button(tb, text=txt, font=FONT_XS,
                      bg=T("ACCENT2"), fg=T("HDR_FG"),
                      relief="flat", cursor="hand2", padx=10, pady=4, bd=0,
                      activebackground=T("ACCENT"), activeforeground="white",
                      command=cmd).pack(side="right", padx=(0, 6))
        frame = tk.Frame(self, bg=T("BG"))
        frame.pack(fill="both", expand=True)
        self._cv = tk.Canvas(frame, bg=T("CARD"), highlightthickness=0)
        hbar = tk.Scrollbar(frame, orient="horizontal", command=self._cv.xview,
                            bg=T("CARD"), troughcolor=T("BG"), relief="flat", bd=0)
        vbar = tk.Scrollbar(frame, orient="vertical", command=self._cv.yview,
                            bg=T("CARD"), troughcolor=T("BG"), relief="flat", bd=0)
        self._cv.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        vbar.pack(side="right", fill="y")
        hbar.pack(side="bottom", fill="x")
        self._cv.pack(fill="both", expand=True)
        threading.Thread(target=self._carregar, daemon=True).start()

    def _carregar(self):
        try:
            from PIL import Image
            ext = os.path.splitext(self._caminho)[1].lower()
            if ext == ".pdf":
                img = pdf_para_imagem(self._caminho, 1200, 1600)
            else:
                img = Image.open(self._caminho).convert("RGB")
            self._pil_img = img
            self.after(0, lambda: self._renderizar(1.0))
        except Exception as e:
            msg = str(e)
            self.after(0, lambda: messagebox.showerror("Erro", msg, parent=self))

    def _renderizar(self, zoom):
        if self._pil_img is None: return
        from PIL import ImageTk
        self._zoom = zoom
        w = int(self._pil_img.width  * zoom)
        h = int(self._pil_img.height * zoom)
        self._img_ref = ImageTk.PhotoImage(self._pil_img.resize((w, h)))
        self._cv.delete("all")
        self._cv.create_image(0, 0, anchor="nw", image=self._img_ref)
        self._cv.configure(scrollregion=(0, 0, w, h))

    def _zoom_in(self):   self._renderizar(min(self._zoom * 1.25, 5.0))
    def _zoom_out(self):  self._renderizar(max(self._zoom / 1.25, 0.1))
    def _zoom_real(self): self._renderizar(1.0)
    def _zoom_fit(self):
        if self._pil_img is None: return
        cw = self._cv.winfo_width()  or 800
        ch = self._cv.winfo_height() or 600
        self._renderizar(min(cw / self._pil_img.width, ch / self._pil_img.height))
