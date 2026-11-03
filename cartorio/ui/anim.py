"""Motor de animacao: curvas de aceleracao, interpolacao de cores e tweens com after()."""
import time

QUADRO_MS = 15


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_out_back(t, s=1.4):
    t -= 1
    return 1 + (s + 1) * t ** 3 + s * t ** 2


def _rgb(cor):
    cor = cor.lstrip("#")
    return tuple(int(cor[i:i + 2], 16) for i in (0, 2, 4))


def misturar(c1, c2, t):
    """Cor entre c1 (t=0) e c2 (t=1), em hexadecimal."""
    a, b = _rgb(c1), _rgb(c2)
    t = max(0.0, min(1.0, t))
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


# Animacoes ativas por (widget, chave): iniciar outra com a mesma chave cancela a anterior
_ativas = {}


def parar(widget, chave):
    job = _ativas.pop((str(widget), chave), None)
    if job:
        try:
            widget.after_cancel(job)
        except Exception:
            pass


def animar(widget, chave, duracao_ms, quadro, ao_fim=None, easing=ease_out_cubic):
    """
    Chama quadro(p) a cada frame com p de 0 a 1 ja suavizado pela curva.
    Para sozinha se o widget for destruido.
    """
    parar(widget, chave)
    inicio = time.perf_counter()
    dur = max(1, duracao_ms) / 1000.0
    k = (str(widget), chave)

    def passo():
        _ativas.pop(k, None)
        try:
            if not widget.winfo_exists():
                return
        except Exception:
            return
        t = min(1.0, (time.perf_counter() - inicio) / dur)
        try:
            quadro(easing(t))
        except Exception:
            return
        if t < 1.0:
            _ativas[k] = widget.after(QUADRO_MS, passo)
        elif ao_fim:
            ao_fim()
    passo()


def animar_cor(widget, prop, destino, duracao_ms=180, origem=None, chave=None):
    """Transicao suave de uma propriedade de cor (bg, fg...)."""
    try:
        inicio = origem or widget.cget(prop)
        if not str(inicio).startswith("#"):
            widget.configure(**{prop: destino})
            return
    except Exception:
        return
    animar(widget, chave or ("cor", prop), duracao_ms,
           lambda p: widget.configure(**{prop: misturar(inicio, destino, p)}))


def realcar(widget, prop, cor_destaque, cor_final, duracao_ms=900):
    """Pisca a propriedade na cor de destaque e volta suavemente."""
    try:
        widget.configure(**{prop: cor_destaque})
    except Exception:
        return
    animar(widget, ("realce", prop), duracao_ms,
           lambda p: widget.configure(**{prop: misturar(cor_destaque, cor_final, p)}),
           easing=ease_in_out_cubic)


def surgir(janela, duracao_ms=170):
    """Fade-in de uma janela (Toplevel ou Tk)."""
    try:
        janela.attributes("-alpha", 0.0)
    except Exception:
        return
    animar(janela, "alpha", duracao_ms,
           lambda p: janela.attributes("-alpha", p))


def sumir(janela, ao_fim, duracao_ms=140):
    """Fade-out de uma janela e depois chama ao_fim."""
    try:
        janela.attributes("-alpha")
    except Exception:
        ao_fim()
        return
    animar(janela, "alpha", duracao_ms,
           lambda p: janela.attributes("-alpha", 1 - p), ao_fim=ao_fim)


class Respiracao:
    """Pulsa uma propriedade de cor entre duas cores enquanto ativa."""

    def __init__(self, widget, prop, cor_a, cor_b, periodo_ms=1400):
        self.widget, self.prop = widget, prop
        self.cor_a, self.cor_b, self.periodo = cor_a, cor_b, periodo_ms
        self.ativa = False

    def iniciar(self):
        if self.ativa:
            return
        self.ativa = True
        self._meia_volta(True)

    def _meia_volta(self, ida):
        if not self.ativa:
            return
        a, b = (self.cor_a, self.cor_b) if ida else (self.cor_b, self.cor_a)
        animar(self.widget, ("respira", self.prop), self.periodo // 2,
               lambda p: self.widget.configure(**{self.prop: misturar(a, b, p)}),
               ao_fim=lambda: self._meia_volta(not ida), easing=ease_in_out_cubic)

    def parar(self, cor_final=None):
        self.ativa = False
        parar(self.widget, ("respira", self.prop))
        if cor_final:
            try:
                self.widget.configure(**{self.prop: cor_final})
            except Exception:
                pass
