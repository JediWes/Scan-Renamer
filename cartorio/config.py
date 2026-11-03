"""Persistencia de configuracoes, preferencias e presets do scanner."""
import json
import os
import sys


def _pasta_base():
    # Arquivos de configuracao ficam ao lado do main.py (ou do executavel).
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = _pasta_base()
CONFIG_FILE = os.path.join(BASE_DIR, "cartorio_config.json")
SCANNER_CONFIG_FILE = os.path.join(BASE_DIR, "scanner_presets.json")


def carregar_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def salvar_config(tipo, pasta, numero):
    try:
        cfg = carregar_config()
        cfg[tipo] = {"pasta": pasta, "numero": numero}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def salvar_preferencias(dados):
    try:
        cfg = carregar_config()
        cfg["_prefs"] = dados
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def carregar_preferencias():
    return carregar_config().get("_prefs", {})


# Chave reservada no arquivo de presets: guarda a ultima configuracao usada.
PRESET_ULTIMO = "__ultimo__"

def carregar_presets():
    try:
        with open(SCANNER_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def salvar_presets(dados):
    try:
        with open(SCANNER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
