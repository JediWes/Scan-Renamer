"""Renomeacao automatica de arquivos novos (watchdog)."""
import os
import re
import threading
import time

from watchdog.events import FileSystemEventHandler

from . import historico

# Caminhos que o monitoramento deve ignorar por alguns segundos
# (ex.: arquivo que acabou de voltar ao nome original ao desfazer).
_ignorados = {}
_ignorados_lock = threading.Lock()


def _chave(caminho):
    return os.path.normcase(os.path.abspath(caminho))


def ignorar_temporariamente(caminho, segundos=10):
    with _ignorados_lock:
        _ignorados[_chave(caminho)] = time.monotonic() + segundos


def _ignorado(caminho):
    agora = time.monotonic()
    with _ignorados_lock:
        for k in [k for k, t in _ignorados.items() if t < agora]:
            del _ignorados[k]
        return _chave(caminho) in _ignorados


class RenomeadorHandler(FileSystemEventHandler):
    def __init__(self, aba, extensoes, delay):
        super().__init__()
        self.aba = aba; self.extensoes = set(extensoes); self.delay = delay
        self._em_processo = set()

    def _ja_renomeado(self, path):
        return bool(re.fullmatch(r"image\d{6}", os.path.splitext(os.path.basename(path))[0]))

    def _deve_tratar(self, p):
        if self._ja_renomeado(p): return False
        if os.path.splitext(p)[1].lower() not in self.extensoes: return False
        if p in self._em_processo: return False
        return not _ignorado(p)

    def on_created(self, event):
        if event.is_directory: return
        p = event.src_path
        if not self._deve_tratar(p): return
        time.sleep(self.delay)
        if _ignorado(p): return
        with self.aba.lock_numero: self._renomear(p)

    def on_moved(self, event):
        if event.is_directory: return
        d = event.dest_path
        if not self._deve_tratar(d): return
        with self.aba.lock_numero: self._renomear(d)

    def _renomear(self, orig):
        if not os.path.exists(orig): return
        self._em_processo.add(orig)
        try:
            ext = os.path.splitext(orig)[1].lower()
            pasta = os.path.dirname(orig)
            n = self.aba.proximo_numero
            while True:
                novo = f"image{n:06d}{ext}"
                novo_c = os.path.join(pasta, novo)
                if not os.path.exists(novo_c): break
                self.aba.log(f"image{n:06d}{ext} já existe, tentando próximo", "warn")
                n += 1
            self.aba.proximo_numero = n
            os.rename(orig, novo_c)
            self.aba.proximo_numero += 1
            self.aba.total_renomeados += 1
            historico.registrar(historico.RENOMEAR, self.aba.tipo, pasta,
                                os.path.basename(orig), novo)
            self.aba.log(f"{os.path.basename(orig)}  →  {novo}", "ok")
            self.aba.atualizar_contador()
            self.aba.flash_notificacao(novo, novo_c)
        except Exception as e:
            self.aba.log(f"Erro ao renomear: {e}", "err")
        finally:
            self._em_processo.discard(orig)
