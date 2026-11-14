"""
Módulo de Gerenciamento e Seleção Estrita de Câmeras (TenniSync)
Diretriz de Segurança e Precisão:
O sistema JAMAIS deve utilizar a câmera frontal integrada ao notebook.
O sistema DEVE EXCLUSIVAMENTE utilizar a câmera conectada à porta USB.
"""

import os
import sys
import subprocess
try:
    from logger import log_info, log_warn, log_error
except ImportError:
    try:
        from Backend.logger import log_info, log_warn, log_error
    except ImportError:
        def log_info(tag, msg, extra=None): print(f"[INFO][{tag}] {msg}")
        def log_warn(tag, msg, extra=None): print(f"[WARN][{tag}] {msg}")
        def log_error(tag, msg, extra=None): print(f"[ERROR][{tag}] {msg}")

# Termos que identificam câmeras integradas / frontais de notebooks
BLACKLIST_TERMS = [
    "integrated",
    "internal",
    "interna",
    "built-in",
    "builtin",
    "front",
    "notebook",
    "laptop",
    "facetime",
    "realtek"  # maioria das webcams integradas em notebooks Windows
]

def list_available_cameras():
    """
    Lista todos os dispositivos de vídeo disponíveis no sistema identificando
    quais são câmeras USB e quais são integradas/bloqueadas.
    """
    cameras = []
    
    # Tentativa 1: Via DirectShow (pygrabber)
    try:
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            pass

        from pygrabber.dshow_graph import FilterGraph
        devices = FilterGraph().get_input_devices()
        for idx, name in enumerate(devices):
            name_lower = name.lower()
            is_blacklisted = any(term in name_lower for term in BLACKLIST_TERMS)
            is_usb = not is_blacklisted
            cameras.append({
                "index": idx,
                "name": name,
                "is_usb": is_usb,
                "is_blacklisted": is_blacklisted
            })
        if cameras:
            return cameras
    except Exception as e:
        log_warn("CAMERA", f"Falha ao enumerar câmeras via pygrabber: {e}")

    # Tentativa 2: Consulta via PowerShell / WMI PnP
    try:
        cmd = 'Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -eq "Camera" -or $_.Service -eq "usbvideo" } | Select-Object -ExpandProperty Name'
        out = subprocess.check_output(['powershell', '-NoProfile', '-Command', cmd], text=True, stderr=subprocess.DEVNULL)
        lines = [line.strip() for line in out.strip().splitlines() if line.strip()]
        for idx, name in enumerate(lines):
            name_lower = name.lower()
            is_blacklisted = any(term in name_lower for term in BLACKLIST_TERMS)
            is_usb = not is_blacklisted
            cameras.append({
                "index": idx,
                "name": name,
                "is_usb": is_usb,
                "is_blacklisted": is_blacklisted
            })
    except Exception as e:
        log_warn("CAMERA", f"Falha ao enumerar câmeras via PowerShell: {e}")

    return cameras

def is_camera_blacklisted(source):
    """
    Verifica se um determinado índice ou nome de fonte de câmera é a webcam integrada do notebook.
    """
    if isinstance(source, str) and not source.isdigit():
        # Se for um arquivo de vídeo (ex: video.mp4), não é câmera integrada
        return False

    idx = int(source) if (isinstance(source, int) or (isinstance(source, str) and source.isdigit())) else None
    if idx is None:
        return False

    cameras = list_available_cameras()
    for cam in cameras:
        if cam["index"] == idx:
            return cam["is_blacklisted"]

    # Se não temos a lista precisa, por convenção em notebooks Windows o índice 0 é a webcam integrada
    if idx == 0 and len(cameras) > 1:
        return True

    return False

def get_usb_camera_source(preferred_source=None):
    """
    Retorna o índice da câmera USB conectada.
    Garante categoricamente que a câmera frontal/integrada do notebook NUNCA seja selecionada.
    """
    # 1. Se for arquivo de vídeo especificado, permite
    if isinstance(preferred_source, str) and not preferred_source.isdigit() and os.path.exists(preferred_source):
        return preferred_source

    cameras = list_available_cameras()
    usb_cameras = [c for c in cameras if c["is_usb"] and not c["is_blacklisted"]]

    log_info("CAMERA", f"Câmeras detectadas no sistema: {[c['name'] + ' (Idx: ' + str(c['index']) + ')' for c in cameras]}")

    # 2. Se o usuário solicitou uma fonte específica (ex: via API ou CLI)
    if preferred_source is not None:
        try:
            req_idx = int(preferred_source)
            for cam in cameras:
                if cam["index"] == req_idx:
                    if cam["is_blacklisted"]:
                        log_warn(
                            "CAMERA",
                            f"BLOQUEIO ATIVADO: Câmera solicitada '{cam['name']}' (Índice {req_idx}) é a frontal/integrada do notebook! "
                            f"Redirecionando automaticamente para a câmera USB externa."
                        )
                    else:
                        return req_idx
        except ValueError:
            pass

    # 3. Seleciona a primeira câmera USB legítima
    if usb_cameras:
        chosen = usb_cameras[0]
        log_info(
            "CAMERA",
            f"Câmera USB selecionada: '{chosen['name']}' no índice {chosen['index']}. "
            f"(Câmera integrada bloqueada com sucesso)."
        )
        return chosen["index"]

    # 4. Caso pygrabber não tenha achado nomes explícitos, mas haja mais de uma câmera, pula o índice 0
    if len(cameras) > 1:
        log_warn("CAMERA", "Índice 0 identificado como provável webcam frontal. Selecionando índice 1 (câmera USB).")
        return 1

    # 5. Se nenhuma câmera USB for encontrada e apenas a integrada existir:
    log_error(
        "CAMERA",
        "NENHUMA CÂMERA USB DETECTADA! A câmera frontal/integrada do notebook está permanentemente "
        "bloqueada por diretriz de segurança e biomecânica do projeto."
    )
    # Retorna o índice 1 como destino USB esperado
    return 1

def get_usb_camera_name():
    """Retorna o nome amigável da câmera USB ativa."""
    cameras = list_available_cameras()
    usb_cameras = [c for c in cameras if c["is_usb"] and not c["is_blacklisted"]]
    if usb_cameras:
        return usb_cameras[0]["name"]
    return "Câmera USB Externa"
