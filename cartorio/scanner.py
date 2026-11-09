"""Digitalizacao via WIA (PowerShell) e montagem de PDF."""
import base64
import json
import os
import queue
import subprocess
import threading
import time


# PowerShell
# Um processo do PowerShell e aberto com antecedencia (ja carregado, sem tocar
# no scanner) e recebe o script por stdin. Cada processo atende UMA operacao com
# o scanner e e encerrado em seguida: so o fim do processo garante que os
# objetos COM do WIA sejam liberados e que outros programas possam usar o
# scanner. Logo depois, um novo processo de reserva e preparado em segundo plano.
# Protocolo: cada script vai em uma linha, codificado em base64; a resposta
# volta em uma linha "<<OK:id>>base64" ou "<<ERR:id>>base64".

class SessaoIndisponivel(Exception):
    """A sessao nao pode ser usada; o script ainda nao foi executado."""


class ErroScript(Exception):
    """O script rodou e terminou com erro."""


def _opcoes_janela_oculta():
    if os.name != "nt":
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    return {"startupinfo": si, "creationflags": subprocess.CREATE_NO_WINDOW}


class SessaoPowerShell:
    COMANDO = ["powershell", "-NoLogo", "-NoProfile", "-NonInteractive",
               "-ExecutionPolicy", "Bypass", "-Command", "-"]

    def __init__(self, comando=None):
        self._comando = comando or self.COMANDO
        self._proc = None
        self._linhas = None
        self._lock = threading.Lock()
        self._seq = 0
        self.desativada = False
        self.finalizada = False

    def _ativa(self):
        return self._proc is not None and self._proc.poll() is None

    def _iniciar(self):
        self.encerrar()
        try:
            self._proc = subprocess.Popen(
                self._comando, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, **_opcoes_janela_oculta())
        except OSError as e:
            self._proc = None
            raise SessaoIndisponivel(str(e))
        self._linhas = queue.Queue()
        proc, fila = self._proc, self._linhas

        def _ler():
            for linha in iter(proc.stdout.readline, b""):
                fila.put(linha.decode("ascii", "ignore").strip())
            fila.put(None)
        threading.Thread(target=_ler, daemon=True).start()

    def executar(self, script, timeout=180, uso_unico=True):
        """
        Executa o script. Com uso_unico (padrao), o processo e encerrado ao
        final e um novo processo de reserva e preparado em segundo plano.
        """
        try:
            return self._executar(script, timeout)
        finally:
            if uso_unico:
                with self._lock:
                    self.encerrar()
                self.preparar()

    def preparar(self):
        """Abre em segundo plano um processo de reserva, sem usar o scanner."""
        if self.desativada or self.finalizada:
            return

        def _abrir():
            try:
                self._executar("$null", 30)
                if self.finalizada:
                    with self._lock:
                        self.encerrar()
            except Exception:
                # Nao respondeu: os scripts passam a usar processo avulso
                self.desativada = True
                with self._lock:
                    self.encerrar()
        threading.Thread(target=_abrir, daemon=True).start()

    def _executar(self, script, timeout):
        with self._lock:
            if not self._ativa():
                self._iniciar()
            self._seq += 1
            ident = str(self._seq)
            b64 = base64.b64encode(script.encode("utf-8")).decode("ascii")
            linha = (
                "$__c=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('" + b64 + "'));"
                "try{$__o=(& ([scriptblock]::Create($__c)) | Out-String);"
                "[Console]::Out.WriteLine('<<OK:" + ident + ">>'+[Convert]::ToBase64String("
                "[Text.Encoding]::UTF8.GetBytes($__o)))}"
                "catch{[Console]::Out.WriteLine('<<ERR:" + ident + ">>'+[Convert]::ToBase64String("
                "[Text.Encoding]::UTF8.GetBytes($_.Exception.Message)))};"
                "[Console]::Out.Flush()\n")
            try:
                self._proc.stdin.write(linha.encode("ascii"))
                self._proc.stdin.flush()
            except OSError as e:
                self.encerrar()
                raise SessaoIndisponivel(str(e))

            limite = time.monotonic() + timeout
            ok, erro = "<<OK:" + ident + ">>", "<<ERR:" + ident + ">>"
            while True:
                resta = limite - time.monotonic()
                if resta <= 0:
                    self.encerrar()
                    raise ErroScript("Tempo esgotado aguardando o scanner.")
                try:
                    resp = self._linhas.get(timeout=resta)
                except queue.Empty:
                    continue
                if resp is None:
                    self.encerrar()
                    raise ErroScript("O PowerShell foi encerrado inesperadamente.")
                if resp.startswith(ok):
                    return base64.b64decode(resp[len(ok):]).decode("utf-8", "replace")
                if resp.startswith(erro):
                    raise ErroScript(base64.b64decode(resp[len(erro):]).decode("utf-8", "replace"))

    def encerrar(self):
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


_sessao = SessaoPowerShell()


def _ps_avulso(script, timeout=180):
    """Executa o script em um processo proprio (modo antigo, usado como reserva)."""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive",
         "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True, text=True, timeout=timeout,
        **_opcoes_janela_oculta())
    return result.stdout.strip(), result.stderr.strip()


def _ps(script, timeout=180):
    """Executa um script PowerShell. Retorna (saida, erro)."""
    if _sessao.desativada:
        return _ps_avulso(script, timeout)
    try:
        return _sessao.executar(script, timeout).strip(), ""
    except ErroScript as e:
        return "", str(e)
    except SessaoIndisponivel:
        return _ps_avulso(script, timeout)


def aquecer_powershell():
    """Prepara um processo de reserva para a primeira operacao ser rapida."""
    _sessao.preparar()


def encerrar_powershell():
    _sessao.finalizada = True
    with _sessao._lock:
        _sessao.encerrar()


# Codigos de erro do WIA mais comuns, traduzidos para o usuario
_ERROS_WIA = {
    "80210006": "O scanner está em uso por outro programa. Feche o outro programa "
                "(ou aguarde ele terminar) e tente de novo.",
    "80210003": "Não há folha no scanner. Insira o documento e tente de novo.",
    "80210002": "Papel enroscado no scanner. Remova a folha e tente de novo.",
    "80210005": "O scanner está desligado ou desconectado.",
    "80210015": "Nenhum scanner disponível. Verifique o cabo ou a conexão.",
    "8021000a": "O scanner está aquecendo. Aguarde alguns segundos e tente de novo.",
    "80210001": "Erro geral do scanner. Desligue e ligue o scanner e tente de novo.",
}


def traduzir_erro_wia(mensagem):
    """Troca codigos HRESULT do WIA por mensagens claras; mantem o resto."""
    baixa = (mensagem or "").lower()
    for codigo, texto in _ERROS_WIA.items():
        if codigo in baixa:
            return texto
    return mensagem


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
    try:
        out, err = _ps(script, timeout=60)
    except Exception:
        return []
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


# Tamanho do papel: rotulo da UI -> (largura, altura) em polegadas.
# None = nao altera (usa o padrao do driver); "max" = maior area aceita pelo scanner.
PAPEIS = {
    "Padrão do driver":           None,
    "A4 (21 × 29,7 cm)":          (8.268, 11.693),
    "Ofício (21,6 × 33 cm)":      (8.504, 12.992),
    "Legal (21,6 × 35,6 cm)":     (8.5, 14.0),
    "Máximo do scanner":          "max",
}
PAPEL_PADRAO = "Padrão do driver"
A4_POL = (8.268, 11.693)


def _linhas_tamanho_papel(papel, resolucao):
    """Comandos PowerShell para a area de leitura. Valores fora do aceito sao limitados."""
    tam = PAPEIS.get(papel)
    if tam is None:
        return []
    if tam == "max":
        larg_mil = "(GetProp $dev.Properties 3076 8500)"     # largura maxima do alimentador
        alt_mil = "(GetProp $dev.Properties 3077 14000)"     # comprimento maximo
        larg_px = alt_px = "999999"
    else:
        larg_mil, alt_mil = str(round(tam[0] * 1000)), str(round(tam[1] * 1000))
        larg_px, alt_px = str(round(tam[0] * resolucao)), str(round(tam[1] * resolucao))
    return [
        "# Tamanho do papel: personalizado (2) com largura/altura em milesimos de polegada",
        "SetProp $dev.Properties 3097 2",
        f"SetProp $dev.Properties 3098 {larg_mil}",
        f"SetProp $dev.Properties 3099 {alt_mil}",
        "# Area de leitura em pixels, a partir do canto superior esquerdo",
        "SetLimitado $item.Properties 6149 0",
        "SetLimitado $item.Properties 6150 0",
        f"SetLimitado $item.Properties 6151 {larg_px}",
        f"SetLimitado $item.Properties 6152 {alt_px}",
    ]


def scanner_uma_pagina(tmp_dir, nome_arquivo,
                        resolucao=300, modo_cor="cor",
                        duplex=False, device_id="", papel=PAPEL_PADRAO):
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
        "function GetProp($col, $id, $padrao) {",
        "    for ($i = 1; $i -le $col.Count; $i++) {",
        "        if ($col.Item($i).PropertyID -eq $id) { return $col.Item($i).Value }",
        "    }",
        "    return $padrao",
        "}",
        "",
        "# Define a propriedade respeitando o intervalo aceito pelo driver",
        "function SetLimitado($col, $id, $val) {",
        "    for ($i = 1; $i -le $col.Count; $i++) {",
        "        $p = $col.Item($i)",
        "        if ($p.PropertyID -eq $id) {",
        "            try {",
        "                if ($p.IsRange) {",
        "                    if ($val -gt $p.SubTypeMax) { $val = $p.SubTypeMax }",
        "                    if ($val -lt $p.SubTypeMin) { $val = $p.SubTypeMin }",
        "                }",
        "                $p.Value = $val",
        "            } catch {}",
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
        *_linhas_tamanho_papel(papel, resolucao),
        "",
        "$resultados = @()",
        "$ultimoErro = $null",
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
        "        $ultimoErro = $_.Exception.Message",
        "        break",
        "    }",
        "}",
        "if ($resultados.Count -eq 0) {",
        "    if ($ultimoErro) { throw $ultimoErro }",
        "    throw 'Nenhuma imagem obtida do scanner.'",
        "}",
        "$resultados | ConvertTo-Json -Compress",
    ]

    script = "\n".join(lines_ps)
    out, err = _ps(script)

    if err and not out.strip():
        if any(c in err.lower() for c in _ERROS_WIA):
            raise Exception(traduzir_erro_wia(err))
        ultimo = [l.strip() for l in err.strip().splitlines() if l.strip()]
        raise Exception(traduzir_erro_wia(ultimo[-1]) if ultimo else "Erro no scanner.")

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


def pagina_em_branco(caminho, limiar=0.0001):
    """
    Indica se a pagina digitalizada esta em branco.
    Analisa em metade da resolucao, ignora 5% de margem (sombras de borda),
    remove pontos isolados de poeira e mede a fracao de pixels escuros.
    O limite e conservador: na duvida, a pagina e mantida.
    """
    from PIL import Image, ImageFilter
    with Image.open(caminho) as im:
        g = im.convert("L")
    w, h = g.size
    if max(w, h) > 1800:
        g = g.resize((w // 2, h // 2), Image.BILINEAR)
        w, h = g.size
    mx, my = int(w * 0.05), int(h * 0.05)
    g = g.crop((mx, my, w - mx, h - my)).filter(ImageFilter.MedianFilter(3))
    hist = g.histogram()
    total = sum(hist) or 1
    acum, fundo = 0, 255
    for v, n in enumerate(hist):
        acum += n
        if acum >= total / 2:
            fundo = v
            break
    # Escuro: abaixo de 75% do tom do papel; tolera papel amarelado e verso vazado claro
    escuros = sum(hist[:int(fundo * 0.75)])
    return escuros / total < limiar


def tamanho_cm(caminho, resolucao):
    """(largura, altura) da imagem em cm, pela resolucao do scan."""
    from PIL import Image
    with Image.open(caminho) as im:
        w, h = im.size
    return w / resolucao * 2.54, h / resolucao * 2.54


def area_limitada(caminho, papel, resolucao, tolerancia=0.97):
    """
    Se o driver entregou uma imagem bem menor que o tamanho pedido, retorna
    (larg_cm, alt_cm) entregues; senao None. Ignora 'Padrao' e 'Maximo'.
    """
    tam = PAPEIS.get(papel)
    if not isinstance(tam, tuple):
        return None
    w_cm, h_cm = tamanho_cm(caminho, resolucao)
    if h_cm < tam[1] * 2.54 * tolerancia:
        return round(w_cm, 1), round(h_cm, 1)
    return None


def _faixas_uniformes(g, eixo, tolerancia):
    """
    Para cada linha (eixo 0) ou coluna (eixo 1) de uma imagem "L", indica se ela
    e uniforme (todos os pixels quase iguais). Retorna lista de (uniforme, media).
    """
    from PIL import Image
    if eixo == 1:
        g = g.transpose(Image.Transpose.TRANSPOSE)
    w, h = g.size
    dados = g.tobytes()
    res = []
    for i in range(h):
        linha = dados[i * w:(i + 1) * w]
        res.append((max(linha) - min(linha) <= tolerancia, sum(linha) / w))
    return res


def aparar_bordas(caminho, resolucao, tolerancia=3):
    """
    Remove o preenchimento que o scanner gera fora da folha quando a area de
    leitura e maior que o papel. O preenchimento e uma cor perfeitamente
    uniforme (branca ou preta); o papel escaneado tem textura e ruido, e o
    conteudo nunca e uniforme, entao nada da folha e cortado.
    Corta dos quatro lados. Retorna True se aparou.
    """
    from PIL import Image
    with Image.open(caminho) as im:
        im.load()
        original = im.copy()
    w, h = original.size
    # Reducao por amostragem simples (NEAREST) preserva o ruido do papel
    f = max(1, max(w, h) // 1400)
    g = original.convert("L").resize((max(1, w // f), max(1, h // f)), Image.NEAREST)
    linhas = _faixas_uniformes(g, 0, tolerancia)
    colunas = _faixas_uniformes(g, 1, tolerancia)

    def limites(faixas):
        ini = next((i for i, (u, _) in enumerate(faixas) if not u), None)
        if ini is None:
            return None
        fim = len(faixas) - next(i for i, (u, _) in enumerate(reversed(faixas)) if not u)
        return ini, fim

    lin, col = limites(linhas), limites(colunas)
    if lin is None or col is None:
        return False   # pagina inteira uniforme: nao mexe
    topo, base = lin[0] * f, min(h, lin[1] * f)
    esq, dir_ = col[0] * f, min(w, col[1] * f)
    # Ignora cortes menores que 2 mm (nao e preenchimento)
    minimo = int(2 / 25.4 * resolucao)
    topo = topo if topo >= minimo else 0
    esq = esq if esq >= minimo else 0
    base = base if h - base >= minimo else h
    dir_ = dir_ if w - dir_ >= minimo else w
    if (topo, esq, base, dir_) == (0, 0, h, w):
        return False
    # Folga de 2 mm so onde o corte encostou em tinta (papel tao branco quanto o
    # preenchimento): ali a borda real da folha nao foi encontrada. Na borda do
    # papel o corte fica rente.
    folga = int(2 / 25.4 * resolucao)

    def tem_tinta(caixa_linha):
        mn, _ = g.crop(caixa_linha).getextrema()
        return mn < 100

    li, lf, ci, cf = lin[0], lin[1] - 1, col[0], col[1] - 1
    caixa = (
        # Cada borda e avaliada so no trecho que permanece na imagem
        max(0, esq - (folga if esq and tem_tinta((ci, li, ci + 1, lf + 1)) else 0)),
        max(0, topo - (folga if topo and tem_tinta((ci, li, cf + 1, li + 1)) else 0)),
        min(w, dir_ + (folga if dir_ < w and tem_tinta((cf, li, cf + 1, lf + 1)) else 0)),
        min(h, base + (folga if base < h and tem_tinta((ci, lf, cf + 1, lf + 1)) else 0)),
    )
    cortada = original.crop(caixa)
    if original.mode == "1":
        cortada.save(caminho, format="TIFF", compression="group4")
    else:
        cortada.save(caminho, format="TIFF", compression="tiff_lzw")
    return True


def ajustar_ao_a4(img, resolucao):
    """
    Coloca a imagem numa pagina A4 na mesma resolucao, reduzindo
    proporcionalmente se ela for maior (como 'ajustar a pagina' da impressora).
    Retorna (imagem, escala aplicada).
    """
    from PIL import Image
    pw, ph = round(A4_POL[0] * resolucao), round(A4_POL[1] * resolucao)
    w, h = img.size
    escala = min(1.0, pw / w, ph / h)
    modo = img.mode
    if escala < 1.0:
        base = img.convert("L") if modo == "1" else img
        nova = base.resize((max(1, round(w * escala)), max(1, round(h * escala))), Image.LANCZOS)
        if modo == "1":
            nova = nova.point(lambda v: 255 if v >= 128 else 0).convert("1", dither=Image.NONE)
    else:
        nova = img
    pagina = Image.new(modo, (pw, ph), 1 if modo == "1" else (255 if modo == "L" else (255, 255, 255)))
    pagina.paste(nova, ((pw - nova.width) // 2, 0))
    return pagina, escala


def tifs_para_pdf(tif_paths, pdf_path, resolucao=300, ajustar_a4=False):
    """
    Une uma lista de TIFs em um unico PDF multipagina. Com ajustar_a4, cada
    pagina vira A4 e as maiores sao reduzidas para caber. Retorna a menor escala.
    """
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
    escalas = []
    if ajustar_a4:
        ajustadas = []
        for im in imgs:
            nova, esc = ajustar_ao_a4(im, resolucao)
            ajustadas.append(nova)
            escalas.append(esc)
            if nova is not im:
                im.close()
        imgs = ajustadas
    imgs[0].save(
        pdf_path, format="PDF", save_all=True,
        append_images=imgs[1:], resolution=float(resolucao),
    )
    for img in imgs:
        try: img.close()
        except Exception: pass
    # Menor escala aplicada (1.0 = nenhuma pagina reduzida)
    return min(escalas) if escalas else 1.0
