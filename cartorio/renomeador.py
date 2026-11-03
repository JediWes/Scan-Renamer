"""Renomeacao automatica de arquivos novos (watchdog)."""
import os
import re
import threading
import time

from watchdog.events import FileSystemEventHandler


class RenomeadorHandler(FileSystemEventHandler):
    def __init__(self, aba, extensoes, delay):
        super().__init__()
        self.aba = aba; self.extensoes = set(extensoes); self.delay = delay
        self._lock = threading.Lock(); self._em_processo = set()

    def _ja_renomeado(self, path):
        return bool(re.fullmatch(r"image\d{6}", os.path.splitext(os.path.basename(path))[0]))

    def on_created(self, event):
        if event.is_directory: return
        p = event.src_path
        if self._ja_renomeado(p): return
        if os.path.splitext(p)[1].lower() not in self.extensoes: return
        if p in self._em_processo: return
        time.sleep(self.delay)
        with self._lock: self._renomear(p)

    def on_moved(self, event):
        if event.is_directory: return
        d = event.dest_path
        if self._ja_renomeado(d): return
        if os.path.splitext(d)[1].lower() not in self.extensoes: return
        if d in self._em_processo: return
        with self._lock: self._renomear(d)

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
            self.aba.log(f"{os.path.basename(orig)}  →  {novo}", "ok")
            self.aba.atualizar_contador()
            self.aba.flash_notificacao(novo, novo_c)
        except Exception as e:
            self.aba.log(f"Erro ao renomear: {e}", "err")
        finally:
            self._em_processo.discard(orig)
