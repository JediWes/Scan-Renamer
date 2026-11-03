"""Numeracao imageNNNNNN, listagem de arquivos e miniaturas."""
import os
import re

PADRAO_NOME = re.compile(r"image(\d{6})", re.IGNORECASE)


def detectar_proximo_numero(pasta):
    maior = -1
    try:
        for nome in os.listdir(pasta):
            m = re.fullmatch(r"image(\d{6})", os.path.splitext(nome)[0], re.IGNORECASE)
            if m:
                n = int(m.group(1))
                if n > maior: maior = n
    except Exception:
        pass
    return maior + 1 if maior >= 0 else None

def contar_arquivos_pasta(pasta, extensoes):
    try:
        return sum(
            1 for f in os.listdir(pasta)
            if os.path.splitext(f)[1].lower() in extensoes
            and re.fullmatch(r"image\d{6}", os.path.splitext(f)[0], re.IGNORECASE)
        )
    except Exception:
        return 0


def listar_para_lote(pasta, extensoes):
    result = []
    try:
        for f in sorted(os.listdir(pasta)):
            ext  = os.path.splitext(f)[1].lower()
            base = os.path.splitext(f)[0]
            if ext in extensoes and not re.fullmatch(r"image\d{6}", base, re.IGNORECASE):
                result.append(f)
    except Exception: pass
    return result


def pdf_para_imagem(caminho, w=160, h=150):
    try:
        import pypdfium2 as pdfium
        doc  = pdfium.PdfDocument(caminho)
        page = doc[0]
        pw, ph = page.get_size()          # API correta: get_size() retorna (w, h)
        scale  = min(w / pw, h / ph) * 2  # 2x para qualidade
        bmp    = page.render(scale=scale)
        img    = bmp.to_pil().convert("RGB")
        img.thumbnail((w, h))
        doc.close()
        return img
    except Exception:
        return None

def carregar_thumbnail(caminho, w=160, h=150):
    ext = os.path.splitext(caminho)[1].lower()
    try:
        from PIL import Image
        if ext == ".pdf":
            return pdf_para_imagem(caminho, w, h)
        img = Image.open(caminho).convert("RGB")
        img.thumbnail((w, h), Image.LANCZOS)
        return img
    except Exception:
        return None
