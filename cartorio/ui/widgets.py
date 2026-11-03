"""Componentes visuais: botao arredondado, abas deslizantes, controle segmentado,
notificacoes, barra de atividade, dicas e campo com texto de exemplo."""
import tkinter as tk
import tkinter.font as tkfont

from ..tema import T, FONT, FONT_SM, FONT_XS, F_ABA, F_BOTAO, F_BOTAO_LG, F_BOTAO_SM, F_BOTAO_XL, F_DISPLAY, F_PEQ_B
from . import anim


def _imagem_arredondada(mestre, w, h, cor, raio, inset=0):
    """Retangulo arredondado suavizado (antialias) como PhotoImage com fundo transparente."""
    from PIL import Image, ImageDraw, ImageTk
    s = 3
    img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    i = inset * s
    d.rounded_rectangle((i, i, w * s - 1 - i, h * s - 1 - i), radius=raio * s, fill=cor)
    return ImageTk.PhotoImage(img.resize((w, h), Image.LANCZOS), master=mestre)


def _fundo_de(pai):
    try:
        return pai.cget("bg")
    except Exception:
        return T("BG")


# Botao

class Botao(tk.Canvas):
    """
    Botao com cantos arredondados, transicao de cor no hover e leve recuo ao pressionar.
    Variantes: primario, secundario, perigo, fantasma.
    Aceita configure(text=..., state=..., variante=...) e ["state"].
    """
    TAMANHOS = {
        "sm": (F_BOTAO_SM, 10, 4),
        "md": (F_BOTAO, 14, 7),
        "lg": (F_BOTAO_LG, 20, 12),
        "xl": (F_BOTAO_XL, 20, 22),
    }
    RAIO = 7

    def __init__(self, pai, texto="", comando=None, variante="primario", tamanho="md",
                 textvariable=None, largura=None, fonte=None, dica=None, **kw):
        fonte_base, self._padx, self._pady = self.TAMANHOS[tamanho]
        f = fonte or fonte_base
        self._fonte = tkfont.nametofont(f) if isinstance(f, str) else tkfont.Font(font=f)
        self._texto = textvariable.get() if textvariable else texto
        self._largura_fixa = largura
        self._comando = comando
        self._variante = variante
        self._estado = "normal"
        self._hover = self._press = False
        self._cache = {}
        linhas = max(1, self._texto.count("\n") + 1)
        h = self._fonte.metrics("linespace") * linhas + 2 * self._pady
        w = largura or self._medir()
        super().__init__(pai, width=w, height=h, bg=_fundo_de(pai), highlightthickness=0,
                         bd=0, cursor="hand2", takefocus=1, **kw)
        self._larg, self._alt = w, h
        self._img = self.create_image(0, 0, anchor="nw")
        self._txt = self.create_text(w / 2, h / 2, text=self._texto, font=self._fonte,
                                     justify="center")
        self._cor = self._cor_alvo()
        self._desenhar(self._cor)
        if textvariable is not None:
            textvariable.trace_add("write", lambda *_: self._definir_texto(textvariable.get()))
        self.bind("<Enter>", self._entrar)
        self.bind("<Leave>", self._sair)
        self.bind("<ButtonPress-1>", self._pressionar)
        self.bind("<ButtonRelease-1>", self._soltar)
        self.bind("<Configure>", self._redimensionar)
        self.bind("<Return>", lambda e: self.invoke())
        self.bind("<space>", lambda e: self.invoke())
        if dica:
            Dica(self, dica)

    # cores

    def _base(self):
        v = self._variante
        if v == "primario":
            return T("ACCENT"), T("TEXT_ON_ACCENT")
        if v == "perigo":
            return T("DANGER"), T("TEXT_ON_ACCENT")
        if v == "fantasma":
            return _fundo_de(self.master), T("HDR_FG")
        return T("BTN_SEC_BG"), T("BTN_SEC_FG")

    def _cor_alvo(self):
        if self._estado == "disabled":
            return T("CARD") if self._variante != "fantasma" else _fundo_de(self.master)
        fundo, _ = self._base()
        if self._press:
            return anim.misturar(fundo, T("TEXT"), 0.22)
        if self._hover:
            alvo = T("ACCENT2") if self._variante == "fantasma" else T("TEXT")
            return anim.misturar(fundo, alvo, 1.0 if self._variante == "fantasma" else 0.12)
        return fundo

    def _cor_texto(self):
        if self._estado == "disabled":
            return T("MUTED")
        _, txt = self._base()
        if self._variante == "fantasma" and self._hover:
            return T("TEXT")
        return txt

    # desenho

    def _medir(self):
        larg = max(self._fonte.measure(l) for l in (self._texto or " ").split("\n"))
        return larg + 2 * self._padx

    def _desenhar(self, cor):
        self._cor = cor
        inset = 1 if self._press else 0
        chave = (self._larg, self._alt, cor, inset)
        img = self._cache.get(chave)
        if img is None:
            if len(self._cache) > 48:
                self._cache.clear()
            img = _imagem_arredondada(self, max(2, self._larg), max(2, self._alt), cor, self.RAIO, inset)
            self._cache[chave] = img
        self.itemconfigure(self._img, image=img)
        if (str(self), "rotulo") not in anim._ativas:
            self.itemconfigure(self._txt, fill=self._cor_texto())

    def _transicao(self, dur=150):
        inicio, fim = self._cor, self._cor_alvo()
        if inicio == fim:
            self._desenhar(fim)
            return
        anim.animar(self, "botao", dur, lambda p: self._desenhar(anim.misturar(inicio, fim, p)))

    def _redimensionar(self, e):
        if (e.width, e.height) != (self._larg, self._alt):
            self._larg, self._alt = e.width, e.height
            self.coords(self._txt, e.width / 2, e.height / 2)
            self._desenhar(self._cor)

    def _definir_texto(self, texto, animar=True):
        anterior, self._texto = self._texto, texto
        if not self._largura_fixa:
            super().configure(width=self._medir())
        if not animar or anterior == texto or not self.winfo_ismapped():
            self.itemconfigure(self._txt, text=texto)
            return
        # O texto antigo sobe e esmaece; o novo entra por baixo
        anim.parar(self, "rotulo")
        for item in self.find_withtag("saindo"):
            self.delete(item)
        velho = self._txt
        self.itemconfigure(velho, tags=("saindo",))
        cx, cy, d = self._larg / 2, self._alt / 2, self._alt * 0.55
        self._txt = self.create_text(cx, cy + d, text=texto, font=self._fonte,
                                     justify="center", fill=self._cor)

        def quadro(p):
            fundo, cor = self._cor, self._cor_texto()
            self.coords(velho, cx, cy - d * p)
            self.itemconfigure(velho, fill=anim.misturar(cor, fundo, min(1, p * 1.6)))
            self.coords(self._txt, cx, cy + d * (1 - p))
            self.itemconfigure(self._txt, fill=anim.misturar(fundo, cor, p))
        anim.animar(self, "rotulo", 260, quadro, ao_fim=lambda: self.delete(velho))

    # eventos

    def _entrar(self, _):
        self._hover = True
        if self._estado == "normal":
            self._transicao()

    def _sair(self, _):
        self._hover = self._press = False
        self._transicao(200)

    def _pressionar(self, _):
        if self._estado != "normal":
            return
        self._press = True
        self._transicao(60)

    def _soltar(self, e):
        if self._estado != "normal" or not self._press:
            return
        self._press = False
        dentro = 0 <= e.x <= self._larg and 0 <= e.y <= self._alt
        self._transicao(120)
        if dentro:
            self.invoke()

    def invoke(self):
        if self._estado == "normal" and self._comando:
            self._comando()

    # API compativel com tk.Button

    def configure(self, cnf=None, **kw):
        mudou = False
        for chave in ("text", "texto"):
            if chave in kw:
                self._definir_texto(kw.pop(chave))
        if "state" in kw:
            self._estado = str(kw.pop("state"))
            super().configure(cursor="hand2" if self._estado == "normal" else "arrow")
            mudou = True
        if "variante" in kw:
            self._variante = kw.pop("variante")
            mudou = True
        if "command" in kw:
            self._comando = kw.pop("command")
        if cnf or kw:
            super().configure(cnf, **kw)
        if mudou:
            self._transicao(220)

    config = configure

    def cget(self, chave):
        if chave == "state":
            return self._estado
        if chave == "text":
            return self._texto
        return super().cget(chave)

    def __getitem__(self, chave):
        return self.cget(chave)


# Abas com indicador deslizante

class AbasDeslizantes(tk.Frame):
    """Abas de texto com sublinhado que desliza ate a aba selecionada."""

    def __init__(self, pai, nomes, ao_selecionar, **kw):
        bg = kw.pop("bg", T("SIDEBAR"))
        super().__init__(pai, bg=bg, **kw)
        self._ao_selecionar = ao_selecionar
        self._labels = {}
        self._atual = None
        linha = tk.Frame(self, bg=bg)
        linha.pack(side="left", padx=(20, 0))
        for nome in nomes:
            lb = tk.Label(linha, text=nome, font=F_ABA, bg=bg, fg=T("MUTED"),
                          padx=14, pady=10, cursor="hand2")
            lb.pack(side="left")
            lb.bind("<Button-1>", lambda e, n=nome: self.selecionar(n))
            lb.bind("<Enter>", lambda e, n=nome: self._hover(n, True))
            lb.bind("<Leave>", lambda e, n=nome: self._hover(n, False))
            lb.bind("<Configure>", lambda e, n=nome: self._realinhar(n))
            self._labels[nome] = lb
        self._ind = tk.Frame(self, bg=T("ACCENT"), height=2)
        self._ind_x = self._ind_w = 0

    def _hover(self, nome, dentro):
        if nome == self._atual:
            return
        anim.animar_cor(self._labels[nome], "fg", T("TEXT") if dentro else T("MUTED"), 140)

    def _realinhar(self, nome):
        """Reposiciona o indicador quando o layout muda (ex.: janela abrindo)."""
        if nome == self._atual and ("{}".format(self), "indicador") not in anim._ativas:
            self._mover(*self._geometria(nome))

    def _geometria(self, nome):
        lb = self._labels[nome]
        return lb.winfo_rootx() - self.winfo_rootx(), lb.winfo_width()

    def selecionar(self, nome, animar=True):
        anterior, self._atual = self._atual, nome
        for n, lb in self._labels.items():
            ativo = n == nome
            anim.animar_cor(lb, "fg", T("TEXT") if ativo else T("MUTED"), 160)
        self.update_idletasks()
        x1, w1 = self._geometria(nome)
        if not animar or anterior is None or self._ind_w == 0:
            self._mover(x1, w1)
        else:
            x0, w0 = self._ind_x, self._ind_w
            anim.animar(self, "indicador", 260,
                        lambda p: self._mover(x0 + (x1 - x0) * p, w0 + (w1 - w0) * p))
        self._ao_selecionar(nome, anterior)

    def _mover(self, x, w):
        self._ind_x, self._ind_w = x, w
        self._ind.place(x=int(x), rely=1.0, y=-2, width=max(1, int(w)), height=2)


# Controle segmentado

class Segmentado(tk.Canvas):
    """Opcoes lado a lado com uma pilula que desliza ate a selecionada."""
    PAD = 3
    RAIO = 6

    def __init__(self, pai, opcoes, ao_selecionar, fonte=FONT, fonte_ativa=F_ABA):
        self._fonte = fonte
        self._fonte_b = fonte_ativa
        self._opcoes = list(opcoes)
        self._ao_selecionar = ao_selecionar
        larg = max(tkfont.nametofont(self._fonte_b).measure(o) for o in self._opcoes) + 36
        self._seg_w = larg
        h = tkfont.nametofont(self._fonte).metrics("linespace") + 16
        w = larg * len(self._opcoes) + 2 * self.PAD
        super().__init__(pai, width=w, height=h + 2 * self.PAD, bg=_fundo_de(pai),
                         highlightthickness=0, bd=0, cursor="hand2")
        self._alt = h
        self._trilho = _imagem_arredondada(self, w, h + 2 * self.PAD, T("CARD"), self.RAIO + 2)
        self.create_image(0, 0, anchor="nw", image=self._trilho)
        self._pilula_img = _imagem_arredondada(self, larg, h, T("ACCENT"), self.RAIO)
        self._pilula = self.create_image(self.PAD, self.PAD, anchor="nw", image=self._pilula_img)
        self._textos = []
        for i, op in enumerate(self._opcoes):
            cx = self.PAD + larg * i + larg / 2
            self._textos.append(self.create_text(cx, self.PAD + h / 2, text=op,
                                                 font=self._fonte, fill=T("SUBTEXT")))
        self._atual = None
        self._x = self.PAD
        self.bind("<Button-1>", self._clique)
        self.bind("<Motion>", self._mover_mouse)
        self.bind("<Leave>", lambda e: self._mover_mouse(None))
        self._sob_mouse = None

    def _indice_em(self, x):
        i = int((x - self.PAD) // self._seg_w)
        return i if 0 <= i < len(self._opcoes) else None

    def _clique(self, e):
        i = self._indice_em(e.x)
        if i is not None:
            self.selecionar(self._opcoes[i])

    def _mover_mouse(self, e):
        i = self._indice_em(e.x) if e is not None else None
        if i == self._sob_mouse:
            return
        self._sob_mouse = i
        for j, t in enumerate(self._textos):
            if self._opcoes[j] != self._atual:
                self.itemconfigure(t, fill=T("TEXT") if j == i else T("SUBTEXT"))

    def selecionar(self, opcao, animar=True):
        if opcao not in self._opcoes:
            return
        i = self._opcoes.index(opcao)
        self._atual = opcao
        x0, x1 = self._x, self.PAD + self._seg_w * i

        def quadro(p):
            self._x = x0 + (x1 - x0) * p
            self.coords(self._pilula, self._x, self.PAD)
            # A cor de cada texto acompanha quanto a pilula esta sobre ele
            for j, t in enumerate(self._textos):
                seg_x = self.PAD + self._seg_w * j
                sob = max(0.0, min(1.0, 1 - abs(self._x - seg_x) / self._seg_w))
                self.itemconfigure(t, fill=anim.misturar(T("SUBTEXT"), T("TEXT_ON_ACCENT"), sob),
                                   font=self._fonte_b if sob > 0.5 else self._fonte)
        if animar and self._x != x1:
            anim.animar(self, "pilula", 300, quadro, easing=anim.ease_out_back)
        else:
            quadro(1)
        self._ao_selecionar(opcao)


# Notificacoes (toasts)

class Notificador:
    """Avisos que deslizam no canto inferior direito e somem sozinhos."""
    MAX = 4
    LARGURA = 340
    MARGEM = 18
    CORES = {"ok": "OK", "info": "ACCENT", "aviso": "WARN", "erro": "ERR"}

    def __init__(self, root):
        self.root = root
        self._ativos = []

    def mostrar(self, titulo, mensagem="", tipo="info", duracao_ms=3800):
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return
        cor = T(self.CORES.get(tipo, "ACCENT"))
        caixa = tk.Frame(self.root, bg=T("CARD"), highlightbackground=T("BORDER"),
                         highlightthickness=1, cursor="hand2")
        tk.Frame(caixa, bg=cor, width=4).pack(side="left", fill="y")
        corpo = tk.Frame(caixa, bg=T("CARD"), padx=12, pady=9)
        corpo.pack(side="left", fill="both", expand=True)
        tk.Label(corpo, text=titulo, font=F_PEQ_B, bg=T("CARD"),
                 fg=T("TEXT"), anchor="w", justify="left",
                 wraplength=self.LARGURA - 40).pack(fill="x")
        if mensagem:
            tk.Label(corpo, text=mensagem, font=FONT_XS, bg=T("CARD"), fg=T("SUBTEXT"),
                     anchor="w", justify="left", wraplength=self.LARGURA - 40).pack(fill="x")
        caixa.update_idletasks()
        item = {"w": caixa, "h": caixa.winfo_reqheight(), "y": 0.0}
        for wd in [caixa, corpo] + list(corpo.winfo_children()):
            wd.bind("<Button-1>", lambda e, it=item: self._fechar(it))
        self._ativos.insert(0, item)
        if len(self._ativos) > self.MAX:
            self._fechar(self._ativos[-1])
        item["y"] = -(item["h"] + 10)
        self._posicionar(item)
        caixa.lift()
        self._reorganizar()
        item["job"] = self.root.after(duracao_ms, lambda: self._fechar(item))

    def _alvo_y(self, item):
        y = self.MARGEM
        for it in self._ativos:
            if it is item:
                return y
            y += it["h"] + 8
        return y

    def _posicionar(self, item):
        item["w"].place(relx=1.0, rely=1.0, anchor="se", x=-self.MARGEM,
                        y=-int(item["y"]), width=self.LARGURA)

    def _reorganizar(self):
        for it in self._ativos:
            y0, y1 = it["y"], self._alvo_y(it)
            if y0 == y1:
                continue

            def quadro(p, it=it, y0=y0, y1=y1):
                it["y"] = y0 + (y1 - y0) * p
                self._posicionar(it)
            anim.animar(it["w"], "toast", 320, quadro, easing=anim.ease_out_back)

    def _fechar(self, item):
        if item not in self._ativos:
            return
        self._ativos.remove(item)
        try:
            self.root.after_cancel(item.get("job"))
        except Exception:
            pass
        w = item["w"]
        x0 = 0

        def quadro(p):
            w.place_configure(x=-self.MARGEM + int((self.LARGURA + 40) * p) + x0)
        anim.animar(w, "toast", 220, quadro, ao_fim=w.destroy, easing=anim.ease_in_out_cubic)
        self._reorganizar()


# Barra de atividade indeterminada

class BarraAtividade(tk.Canvas):
    def __init__(self, pai, altura=3):
        super().__init__(pai, height=altura, bg=_fundo_de(pai), highlightthickness=0, bd=0)
        self._seg = self.create_rectangle(0, 0, 0, altura, fill=T("ACCENT"), width=0)
        self._alt = altura
        self._ativa = False

    def iniciar(self):
        if self._ativa:
            return
        self._ativa = True
        self.configure(bg=T("CARD"))
        self._ciclo()

    def _ciclo(self):
        if not self._ativa:
            return

        def quadro(p):
            w = max(1, self.winfo_width())
            seg = w * 0.35
            x = -seg + (w + seg) * p
            self.coords(self._seg, x, 0, x + seg, self._alt)
        anim.animar(self, "atividade", 1100, quadro, ao_fim=self._ciclo,
                    easing=anim.ease_in_out_cubic)

    def parar(self):
        self._ativa = False
        anim.parar(self, "atividade")
        self.coords(self._seg, 0, 0, 0, self._alt)
        self.configure(bg=_fundo_de(self.master))


# Dica ao passar o mouse

class Dica:
    ATRASO_MS = 550

    def __init__(self, widget, texto):
        self.widget, self.texto = widget, texto
        self._job = self._janela = None
        widget.bind("<Enter>", self._agendar, add="+")
        widget.bind("<Leave>", self._esconder, add="+")
        widget.bind("<ButtonPress>", self._esconder, add="+")

    def _agendar(self, _):
        self._cancelar()
        self._job = self.widget._root().after(self.ATRASO_MS, self._mostrar)

    def _cancelar(self):
        if self._job:
            try:
                self.widget._root().after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def _mostrar(self):
        self._job = None
        try:
            if self._janela or not self.widget.winfo_exists():
                return
        except tk.TclError:
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        j = tk.Toplevel(self.widget)
        j.overrideredirect(True)
        j.configure(bg=T("BORDER"))
        tk.Label(j, text=self.texto, font=FONT_XS, bg=T("CARD"), fg=T("TEXT"),
                 padx=8, pady=4, justify="left", wraplength=280).pack(padx=1, pady=1)
        j.geometry(f"+{x}+{y}")
        self._janela = j
        anim.surgir(j, 140)

    def _esconder(self, _=None):
        self._cancelar()
        if self._janela:
            try:
                self._janela.destroy()
            except Exception:
                pass
            self._janela = None


# Campo de texto com exemplo

class CampoTexto(tk.Entry):
    """
    Entry com texto de exemplo quando vazio e borda que acende no foco.
    O exemplo e um rotulo sobreposto: a variavel nunca recebe esse texto.
    """

    def __init__(self, pai, textvariable, exemplo="", **kw):
        kw.setdefault("font", FONT_SM)
        super().__init__(pai, textvariable=textvariable, bg=T("ENTRY_BG"), fg=T("TEXT"),
                         insertbackground=T("TEXT"), relief="flat", bd=0,
                         highlightbackground=T("BORDER"), highlightcolor=T("ACCENT"),
                         highlightthickness=1, **kw)
        self._var = textvariable
        self._rotulo = None
        if exemplo:
            self._rotulo = tk.Label(self, text=exemplo, font=kw["font"], bg=T("ENTRY_BG"),
                                    fg=T("MUTED"), cursor="xterm")
            self._rotulo.bind("<Button-1>", lambda e: self.focus_set())
            textvariable.trace_add("write", lambda *_: self._atualizar())
            self.bind("<FocusIn>", lambda e: self._atualizar(), add="+")
            self.bind("<FocusOut>", lambda e: self._atualizar(), add="+")
            self._atualizar()

    def _atualizar(self):
        if self._rotulo is None:
            return
        if self._var.get():
            self._rotulo.place_forget()
        else:
            self._rotulo.place(x=6, rely=0.5, anchor="w")


# Numero em estilo odometro

class Odometro(tk.Canvas):
    """
    Mostra o valor de uma StringVar com fonte mono; quando muda, so os caracteres
    alterados rolam (para cima se o numero cresce, para baixo se diminui).
    Clique para editar: um campo aparece no lugar e Enter confirma.
    """
    PADX, PADY = 14, 8

    def __init__(self, pai, variavel, caracteres=11, fonte=F_DISPLAY, cor=None, fundo=None,
                 validar=None, dica=None):
        self._fonte = tkfont.nametofont(fonte)
        self._fonte_nome = fonte
        self._cw = self._fonte.measure("0")
        self._lh = self._fonte.metrics("linespace")
        self._cor = cor or T("OK")
        self._fundo = fundo or T("ENTRY_BG")
        self._var = variavel
        self._validar = validar or (lambda v: True)
        w = self._cw * caracteres + 2 * self.PADX
        h = self._lh + 2 * self.PADY
        super().__init__(pai, width=w, height=h, bg=self._fundo, highlightthickness=1,
                         highlightbackground=T("BORDER"), bd=0, cursor="xterm")
        self._larg, self._alt = w, h
        self._itens = []
        self._valor = ""
        self._desenhar_estatico(variavel.get())
        self._trace = variavel.trace_add("write", lambda *_: self._mudou())
        self.bind("<Destroy>", self._remover_trace, add="+")
        self.bind("<Button-1>", lambda e: self.editar())
        self.bind("<Enter>", lambda e: self.configure(highlightbackground=T("ACCENT")))
        self.bind("<Leave>", lambda e: self.configure(highlightbackground=T("BORDER")))
        self._entrada = None
        if dica:
            Dica(self, dica)

    def _remover_trace(self, _=None):
        try:
            self._var.trace_remove("write", self._trace)
        except Exception:
            pass

    def _x(self, i, n):
        inicio = (self._larg - self._cw * n) / 2
        return inicio + self._cw * i + self._cw / 2

    def _desenhar_estatico(self, valor):
        for it in self._itens:
            self.delete(it)
        cy = self._alt / 2
        self._itens = [self.create_text(self._x(i, len(valor)), cy, text=c, font=self._fonte_nome,
                                        fill=self._cor) for i, c in enumerate(valor)]
        self._valor = valor

    def _numero(self, valor):
        dig = "".join(c for c in valor if c.isdigit())
        return int(dig) if dig else None

    def _mudou(self):
        novo, velho = self._var.get(), self._valor
        if novo == velho:
            return
        if len(novo) != len(velho) or not self.winfo_ismapped():
            self._desenhar_estatico(novo)
            return
        a, b = self._numero(velho), self._numero(novo)
        sentido = -1 if (a is not None and b is not None and b < a) else 1
        cy, d = self._alt / 2, self._lh * 0.9
        anim.parar(self, "odometro")
        self._desenhar_estatico(velho)
        mudam = [i for i, (x, y) in enumerate(zip(velho, novo)) if x != y]
        pares = []
        for i in mudam:
            sai = self._itens[i]
            entra = self.create_text(self._x(i, len(novo)), cy + d * sentido, text=novo[i],
                                     font=self._fonte_nome, fill=self._fundo)
            pares.append((i, sai, entra))
        self._valor = novo
        n = len(novo)

        def quadro(p):
            for i, sai, entra in pares:
                # Digitos mais a direita rolam primeiro, como num odometro
                atraso = (n - 1 - i) * 0.06
                q = max(0.0, min(1.0, (p - atraso) / max(0.01, 1 - atraso)))
                q = anim.ease_out_back(q, 1.2) if q < 1 else 1
                x = self._x(i, n)
                self.coords(sai, x, cy - d * sentido * q)
                self.itemconfigure(sai, fill=anim.misturar(self._cor, self._fundo, min(1, q * 1.4)))
                self.coords(entra, x, cy + d * sentido * (1 - q))
                self.itemconfigure(entra, fill=anim.misturar(self._fundo, self._cor, min(1, q)))

        def fim():
            for i, sai, entra in pares:
                self.delete(sai)
                self._itens[i] = entra
        anim.animar(self, "odometro", 380 + 30 * len(pares), quadro, ao_fim=fim,
                    easing=lambda t: t)

    def realcar(self, cor):
        anim.realcar(self, "bg", cor, self._fundo, 1100)

    # edicao

    def editar(self):
        if self._entrada is not None:
            return
        tmp = tk.StringVar(value=self._var.get())
        e = tk.Entry(self, textvariable=tmp, font=self._fonte_nome, justify="center",
                     bg=self._fundo, fg=self._cor, insertbackground=self._cor,
                     relief="flat", bd=0, highlightthickness=0)
        e.place(x=0, y=0, relwidth=1, relheight=1)
        e.focus_set()
        e.select_range(0, "end")
        self._entrada = e

        def confirmar(_=None):
            v = tmp.get().strip().lower()
            fechar()
            if self._validar(v):
                self._var.set(v)
            else:
                self.realcar(anim.misturar(T("ERR"), self._fundo, 0.55))

        def fechar(_=None):
            if self._entrada is not None:
                self._entrada.destroy()
                self._entrada = None
        e.bind("<Return>", confirmar)
        e.bind("<KP_Enter>", confirmar)
        e.bind("<FocusOut>", confirmar)
        e.bind("<Escape>", fechar)
