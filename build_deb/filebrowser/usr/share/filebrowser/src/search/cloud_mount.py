"""
Filebrowser — Montagem Automática de Nuvem

Monta e desmonta diretórios de nuvem via rclone mount/fusermount.
Detecta mounts já ativos para evitar conflitos.
"""

import logging
import os
import subprocess
import time
from pathlib import Path

log = logging.getLogger(__name__)


def _read_proc_mounts() -> set[str]:
    """Lê /proc/mounts e retorna os pontos de montagem ativos."""
    mounts = set()
    try:
        with open("/proc/mounts", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    mounts.add(parts[1])
    except OSError:
        pass
    return mounts


def is_mounted(mount_point: Path) -> bool:
    """
    Verifica se um diretório já está montado.
    Checa via /proc/mounts (mais confiável que listar conteúdo).
    """
    resolved = str(mount_point.resolve())
    active_mounts = _read_proc_mounts()
    return resolved in active_mounts


def mount_cloud(remote: str, mount_point: Path, timeout: int = 15) -> bool:
    """
    Monta um remote rclone no ponto de montagem especificado.

    Args:
        remote: Nome do remote rclone (ex: "onedrive").
        mount_point: Caminho do diretório de montagem.
        timeout: Segundos para aguardar a montagem ficar pronta.

    Returns:
        True se montado com sucesso, False caso contrário.
    """
    mount_point = mount_point.resolve()

    # Já montado? Pula.
    if is_mounted(mount_point):
        log.info("Já montado: %s → %s", remote, mount_point)
        return True

    # Garantir que o diretório existe
    mount_point.mkdir(parents=True, exist_ok=True)

    cmd = [
        "rclone", "mount",
        f"{remote}:",
        str(mount_point),
        "--vfs-cache-mode", "full",
        "--daemon",
        "--daemon-wait", "0",
    ]

    log.info("Montando: %s → %s", remote, mount_point)
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as e:
        log.error("Falha ao montar %s: %s", remote, e.stderr.strip())
        return False
    except subprocess.TimeoutExpired:
        log.error("Timeout ao montar %s", remote)
        return False
    except FileNotFoundError:
        log.error("rclone não encontrado no PATH")
        return False

    # Aguardar montagem ficar disponível
    for _ in range(timeout * 2):
        if is_mounted(mount_point):
            log.info("Montado com sucesso: %s", remote)
            return True
        time.sleep(0.5)

    log.warning("Montagem de %s não confirmada após %ds", remote, timeout)
    # Checa se tem conteúdo como fallback
    try:
        if any(mount_point.iterdir()):
            log.info("Montagem de %s confirmada via conteúdo", remote)
            return True
    except OSError:
        pass

    return False


def unmount_cloud(mount_point: Path) -> bool:
    """
    Desmonta um ponto de montagem FUSE via fusermount.

    Returns:
        True se desmontado com sucesso, False caso contrário.
    """
    mount_point = mount_point.resolve()

    if not is_mounted(mount_point):
        return True  # Já desmontado

    log.info("Desmontando: %s", mount_point)
    try:
        subprocess.run(
            ["fusermount", "-u", str(mount_point)],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return True
    except subprocess.CalledProcessError as e:
        log.warning("Falha ao desmontar %s: %s", mount_point, e.stderr.strip())
        # Tentar forçar
        try:
            subprocess.run(
                ["fusermount", "-uz", str(mount_point)],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def mount_all(remotes: dict[str, str]) -> dict[str, bool]:
    """
    Monta todos os remotes configurados.

    Args:
        remotes: Dicionário {nome_remote: caminho_montagem}
                 Ex: {"onedrive": "~/Nuvem/OneDrive"}

    Returns:
        Dicionário {nome_remote: sucesso_bool}
    """
    results = {}
    for remote, mount_path in remotes.items():
        path = Path(mount_path).expanduser().resolve()
        results[remote] = mount_cloud(remote, path)
    return results


def unmount_all(remotes: dict[str, str]) -> dict[str, bool]:
    """
    Desmonta todos os remotes configurados.

    Args:
        remotes: Dicionário {nome_remote: caminho_montagem}

    Returns:
        Dicionário {nome_remote: sucesso_bool}
    """
    results = {}
    for remote, mount_path in remotes.items():
        path = Path(mount_path).expanduser().resolve()
        results[remote] = unmount_cloud(path)
    return results
