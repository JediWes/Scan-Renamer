"""Historico persistente de renomeacoes e digitalizacoes (CSV)."""
import csv
import os
import threading
import time

from .config import BASE_DIR

ARQUIVO = os.path.join(BASE_DIR, "historico.csv")
CAMPOS = ["data_hora", "acao", "tipo", "pasta", "de", "para"]

# Acoes registradas
RENOMEAR = "renomear"     # monitoramento automatico
LOTE     = "lote"         # renomeacao em lote
SCANNER  = "scanner"      # PDF gerado pela aba Scanner
DESFAZER = "desfazer"     # reversao de uma renomeacao

DESFAZIVEIS = (RENOMEAR, LOTE)

_lock = threading.Lock()


def registrar(acao, tipo, pasta, de, para):
    linha = {
        "data_hora": time.strftime("%Y-%m-%d %H:%M:%S"),
        "acao": acao, "tipo": tipo or "", "pasta": pasta or "",
        "de": de or "", "para": para or "",
    }
    with _lock:
        novo = not os.path.exists(ARQUIVO)
        try:
            # utf-8-sig e ';' para abrir corretamente no Excel em portugues
            with open(ARQUIVO, "a", encoding="utf-8-sig" if novo else "utf-8",
                      newline="") as f:
                w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";")
                if novo:
                    w.writeheader()
                w.writerow(linha)
        except OSError:
            pass
    return linha


def ler():
    with _lock:
        try:
            with open(ARQUIVO, "r", encoding="utf-8-sig", newline="") as f:
                return list(csv.DictReader(f, delimiter=";"))
        except (OSError, csv.Error):
            return []


def _pilha_desfaziveis(linhas):
    """Renomeacoes ainda nao desfeitas, na ordem em que ocorreram."""
    pilha = []
    for ln in linhas:
        if ln.get("acao") in DESFAZIVEIS:
            pilha.append(ln)
        elif ln.get("acao") == DESFAZER:
            # Remove a renomeacao mais recente que corresponde a esta reversao
            for i in range(len(pilha) - 1, -1, -1):
                p = pilha[i]
                if p["pasta"] == ln["pasta"] and p["para"] == ln["de"] and p["de"] == ln["para"]:
                    del pilha[i]
                    break
    return pilha


def ultima_desfazivel():
    pilha = _pilha_desfaziveis(ler())
    return pilha[-1] if pilha else None


def desfazer(entrada, antes_de_renomear=None):
    """
    Reverte a renomeacao 'entrada'. Retorna (ok, mensagem).
    antes_de_renomear(caminho_original) e chamado antes do os.rename, para que
    o monitoramento ignore o arquivo que volta ao nome original.
    """
    pasta = entrada["pasta"]
    atual = os.path.join(pasta, entrada["para"])
    original = os.path.join(pasta, entrada["de"])
    if not os.path.exists(atual):
        return False, f"{entrada['para']} não existe mais na pasta."
    if os.path.exists(original):
        return False, f"Já existe um arquivo chamado {entrada['de']} na pasta."
    if antes_de_renomear:
        antes_de_renomear(original)
    try:
        os.rename(atual, original)
    except OSError as e:
        return False, f"Não foi possível renomear: {e}"
    registrar(DESFAZER, entrada["tipo"], pasta, entrada["para"], entrada["de"])
    return True, f"{entrada['para']}  →  {entrada['de']}"
