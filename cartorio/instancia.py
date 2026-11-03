"""Garante uma unica instancia do app aberta por computador."""
import socket
import threading

PORTA = 47613
MENSAGEM = b"mostrar"


class InstanciaUnica:
    """
    A primeira instancia ocupa uma porta local. Uma segunda instancia nao
    consegue ocupa-la, avisa a primeira (que traz a janela para frente) e encerra.
    """

    def __init__(self, porta=PORTA):
        self.porta = porta
        self._sock = None

    def adquirir(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            # Windows: impede que outro processo ocupe a mesma porta com reuse
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            s.bind(("127.0.0.1", self.porta))
            s.listen(2)
        except OSError:
            s.close()
            return False
        self._sock = s
        return True

    def avisar_existente(self):
        """Pede a instancia ja aberta para aparecer. Retorna True se ela respondeu."""
        try:
            with socket.create_connection(("127.0.0.1", self.porta), timeout=2) as c:
                c.sendall(MENSAGEM)
            return True
        except OSError:
            return False

    def ouvir(self, ao_receber):
        if self._sock is None:
            return
        sock = self._sock

        def _loop():
            while True:
                try:
                    conn, _ = sock.accept()
                except OSError:
                    return
                with conn:
                    try:
                        conn.settimeout(2)
                        if conn.recv(32).startswith(MENSAGEM):
                            ao_receber()
                    except OSError:
                        pass
        threading.Thread(target=_loop, daemon=True).start()

    def liberar(self):
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
