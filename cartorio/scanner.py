"""Digitalizacao via WIA (PowerShell) e montagem de PDF."""
import json
import os
import subprocess


def _ps(script):
    """Executa PowerShell sem exibir janela para o usuário."""
    si = subprocess.STARTUPINFO()
    si.dwFlags  |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0   # SW_HIDE
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive",
         "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True, text=True, timeout=120,
        startupinfo=si,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return result.stdout.strip(), result.stderr.strip()

def scanner_listar_dispositivos():
    """Retorna lista de (nome, deviceId) dos scanners WIA disponíveis."""
    script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$dm = New-Object -ComObject WIA.DeviceManager
$result = @()
for ($i = 1; $i -le $dm.DeviceInfos.Count; $i++) {
    $di = $dm.DeviceInfos.Item($i)
    if ($di.Type -eq 1) {
        $result += ($di.Properties.Item('Name').Value + '|' + $di.DeviceID)
    }
}
$result -join ';;'
"""
    out, err = _ps(script)
    if not out.strip():
        return []
    devices = []
    for entry in out.strip().split(';;'):
        entry = entry.strip()
        if '|' in entry:
            nome, did = entry.split('|', 1)
            devices.append((nome.strip(), did.strip()))
        elif entry:
            devices.append((entry, ''))
    return devices


# Modo de cor: rotulo da UI -> chave interna.
# WIA DataType (4106): 0 = P&B 1 bit, 1 = tons de cinza, 2 = colorido.
# WIA Intent (6146):   1 = cor, 2 = cinza, 4 = texto (P&B).
MODOS_COR_LABEL = {"Colorido": "cor", "Cinza": "cinza", "PretoBranco": "pb"}
_WIA_COR = {
    "cor":   {"datatype": 2, "bpp": 24, "intent": 1},
    "cinza": {"datatype": 1, "bpp": 8,  "intent": 2},
    "pb":    {"datatype": 0, "bpp": 1,  "intent": 4},
}


def aplicar_modo_cor(caminho, modo_cor):
    """Garante o modo de cor no arquivo, mesmo se o driver ignorar o WIA."""
    from PIL import Image
    if modo_cor == "cor":
        return
    with Image.open(caminho) as im:
        im.load()
        if modo_cor == "cinza":
            if im.mode == "L":
                return
            out = im.convert("L")
            out.save(caminho, format="TIFF", compression="tiff_lzw")
        else:
            if im.mode == "1":
                return
            out = im.convert("L").point(lambda v: 255 if v >= 140 else 0).convert("1", dither=Image.NONE)
            out.save(caminho, format="TIFF", compression="group4")


def scanner_uma_pagina(tmp_dir, nome_arquivo,
                        resolucao=300, modo_cor="cor",
                        duplex=False, device_id=""):
    """
    Escaneia uma passagem do ADF e retorna a lista de TIFs gerados.
    - Simplex: 1 Transfer() = 1 TIF (frente)
    - Duplex: 1 passagem = 2 Transfer() (frente e verso)
    O modo de cor e pedido ao driver e depois reforcado por pos-processamento.
    """
    cfg       = _WIA_COR.get(modo_cor, _WIA_COR["cor"])
    dup_sel   = 5 if duplex else 1
    n_imgs    = 2 if duplex else 1
    pasta_ps  = tmp_dir.replace("\\", "/")
    base_dest = pasta_ps + "/" + nome_arquivo

    lines_ps = [
        "$ErrorActionPreference = 'Stop'",
        "",
        "function SetProp($col, $id, $val) {",
        "    for ($i = 1; $i -le $col.Count; $i++) {",
        "        if ($col.Item($i).PropertyID -eq $id) {",
        "            try { $col.Item($i).Value = $val } catch {}",
        "            return",
        "        }",
        "    }",
        "}",
        "",
        "$dm = New-Object -ComObject WIA.DeviceManager",
        "$devInfo = $null",
        "for ($i = 1; $i -le $dm.DeviceInfos.Count; $i++) {",
        "    $di = $dm.DeviceInfos.Item($i)",
        "    if ($di.Type -eq 1) {",
        f"        if ('{device_id}' -eq '' -or $di.DeviceID -eq '{device_id}') {{",
        "            $devInfo = $di; break",
        "        }",
        "    }",
        "}",
        "if ($null -eq $devInfo) { throw 'Scanner nao encontrado.' }",
        "$dev  = $devInfo.Connect()",
        "$item = $dev.Items.Item(1)",
        "# Intent primeiro: alterar o intent redefine outras propriedades",
        f"SetProp $item.Properties 6146 {cfg['intent']}",
        f"SetProp $item.Properties 4106 {cfg['datatype']}",
        f"SetProp $item.Properties 4104 {cfg['bpp']}",
        f"SetProp $item.Properties 6147 {resolucao}",
        f"SetProp $item.Properties 6148 {resolucao}",
        f"SetProp $dev.Properties  3088 {dup_sel}",
        f"SetProp $dev.Properties  3081 {n_imgs}",
        "",
        "$resultados = @()",
        f"$limite = {n_imgs}",
        "$idx = 1",
        "while ($idx -le $limite) {",
        "    try {",
        f"        $dest = '{base_dest}_' + $idx.ToString('00') + '.tif'",
        "        $img  = $item.Transfer()",
        "        $img.SaveFile($dest)",
        "        $resultados += $dest",
        "        $idx++",
        "    } catch {",
        "        break",
        "    }",
        "}",
        "if ($resultados.Count -eq 0) { throw 'Nenhuma imagem obtida do scanner.' }",
        "$resultados | ConvertTo-Json -Compress",
    ]

    script = "\n".join(lines_ps)
    out, err = _ps(script)

    if err and not out.strip():
        ultimo = [l.strip() for l in err.strip().splitlines() if l.strip()]
        raise Exception(ultimo[-1] if ultimo else "Erro no scanner.")

    try:
        data = json.loads(out.strip())
        paths = data if isinstance(data, list) else ([data] if data else [])
        paths = [p.replace("/", os.sep) for p in paths if p]
    except Exception:
        paths = [out.strip().replace("/", os.sep)] if out.strip() else []

    for p in paths:
        try:
            aplicar_modo_cor(p, modo_cor)
        except Exception:
            pass
    return paths


def tifs_para_pdf(tif_paths, pdf_path, resolucao=300):
    """Une uma lista de TIFs em um único PDF multi-página."""
    from PIL import Image
    imgs = []
    for p in tif_paths:
        try:
            im = Image.open(p)
            im.load()
            imgs.append(im if im.mode in ("1", "L", "RGB") else im.convert("RGB"))
        except Exception:
            pass
    if not imgs:
        raise Exception("Nenhuma imagem válida para gerar o PDF.")
    imgs[0].save(
        pdf_path, format="PDF", save_all=True,
        append_images=imgs[1:], resolution=float(resolucao),
    )
    for img in imgs:
        try: img.close()
        except Exception: pass
