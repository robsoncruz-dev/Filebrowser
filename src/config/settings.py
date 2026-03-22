"""
Filebrowser — Módulo de Configuração

Carrega e gerencia as configurações da aplicação a partir do config.toml.
"""

import tomllib
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field


__version__ = "0.4.4"

# Caminho raiz do projeto (dois níveis acima de src/config/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Define directories based on the OS
if sys.platform == "win32":
    app_data = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    local_app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    USER_CONFIG_DIR = app_data / "Filebrowser"
    CACHE_DIR = local_app_data / "Filebrowser" / "Cache"
else:
    USER_CONFIG_DIR = Path.home() / ".config" / "filebrowser"
    CACHE_DIR = Path.home() / ".cache" / "filebrowser"

USER_CONFIG_FILE = USER_CONFIG_DIR / "config.toml"
PROJECT_CONFIG_FILE = PROJECT_ROOT / "config.toml"

# Usar config do usuário se existir, senão o do projeto
CONFIG_FILE = USER_CONFIG_FILE if USER_CONFIG_FILE.exists() else PROJECT_CONFIG_FILE

DB_PATH = CACHE_DIR / "index.db"


@dataclass
class SearchConfig:
    """Configurações de busca."""
    if sys.platform == "win32":
        # Pastas comuns no Windows
        default_dirs = ["~/Documents", "~/Downloads"]
    else:
        default_dirs = ["~/Documentos", "~/Downloads"]

    diretorios: list[str] = field(default_factory=lambda: SearchConfig.default_dirs)
    profundidade_local: int = 5
    profundidade_nuvem: int = 15
    ignorar: list[str] = field(default_factory=lambda: [".cache", "node_modules", ".git", "AppData", "Local Settings"])
    prefixo_nuvem: str = "~/Nuvem"
    diretorios_nuvem_nativa: list[str] = field(default_factory=list)


    @property
    def diretorios_expandidos(self) -> list[Path]:
        """Retorna os diretórios de busca com ~ expandido (incluindo mídias externas dinâmicas)."""
        paths = []
        for d in self.diretorios:
            p = Path(d).expanduser().resolve()
            if p.exists() and p.is_dir() and p not in paths:
                paths.append(p)
                
        # Detecção Híbrida Mídia Externa (Discos e HDs secundarios via psutil)
        try:
            import psutil
            for part in psutil.disk_partitions(all=False):
                if not part.mountpoint or 'cdrom' in part.opts or part.fstype == '':
                    continue
                
                mp = Path(part.mountpoint).resolve()
                
                if sys.platform == "win32":
                    # Evitar C:\ root para não varrer sistema, pois ~/ já é lido no C:
                    if str(mp).upper().startswith("C:\\"):
                        continue
                else:
                    # Em Linux, evitar root, /boot e dependências do sistema
                    if str(mp) == "/" or str(mp).startswith("/boot") or str(mp).startswith("/snap"):
                        continue
                        
                if mp.exists() and mp.is_dir() and mp not in paths:
                    paths.append(mp)
        except (ImportError, OSError):
            pass
            
        return paths

    @property
    def diretorios_locais(self) -> list[Path]:
        """Retorna apenas os diretórios locais estritos (não-nuvem e não rclone)."""
        nuvem = Path(self.prefixo_nuvem).expanduser().resolve()
        
        # Filtra pastas de Rclone
        base_locais = [p for p in self.diretorios_expandidos if not str(p).startswith(str(nuvem))]
        
        # Filtra pastas Nativas de Nuvem (OneDrive/GDrive)
        locais_estritos = []
        for p in base_locais:
            is_cloud = False
            p_str = str(p)
            p_lower = p_str.lower()
            
            # Fuzzy check against known Cloud directory names in path
            if "onedrive" in p_lower or "google drive" in p_lower or "gdrive" in p_lower or "meu drive" in p_lower or "my drive" in p_lower:
                is_cloud = True
            else:
                for c in self.diretorios_nuvem_nativa:
                    if p_str.startswith(str(Path(c).resolve())):
                        is_cloud = True
                        break
                        
            if not is_cloud:
                locais_estritos.append(p)
                
        return locais_estritos

    @property
    def diretorios_nuvem_nativos_expandidos(self) -> list[Path]:
        """Retorna instâncias de pastas locais do Windows que atuam como Nuvens."""
        paths = []
        
        # Add explicit paths from settings
        for d in self.diretorios_nuvem_nativa:
            p = Path(d).expanduser().resolve()
            if p.exists() and p.is_dir() and p not in paths:
                paths.append(p)
                
        # Also retroactively extract fuzzy matches from all indexed directories
        for p in self.diretorios_expandidos:
            p_str = str(p).lower()
            if "onedrive" in p_str or "google drive" in p_str or "gdrive" in p_str or "meu drive" in p_str or "my drive" in p_str:
                if p not in paths:
                    paths.append(p)
                    
        return paths

    @property
    def diretorios_nuvem(self) -> list[Path]:
        """Retorna apenas os diretórios de nuvem virtuais (rclone)."""
        nuvem = Path(self.prefixo_nuvem).expanduser().resolve()
        return [p for p in self.diretorios_expandidos if str(p).startswith(str(nuvem))]


@dataclass
class InterfaceConfig:
    """Configurações da interface."""
    largura: int = 620
    max_resultados: int = 12


@dataclass
class GeralConfig:
    """Configurações gerais."""
    leitor: str = "zathura"
    fechar_apos_abrir: bool = True


@dataclass
class CloudConfig:
    """Configurações de montagem de nuvem."""
    auto_montar: bool = False
    remotes: dict[str, str] = field(default_factory=dict)


@dataclass
class AppConfig:
    """Configuração completa da aplicação."""
    geral: GeralConfig = field(default_factory=GeralConfig)
    busca: SearchConfig = field(default_factory=SearchConfig)
    interface: InterfaceConfig = field(default_factory=InterfaceConfig)
    nuvem: CloudConfig = field(default_factory=CloudConfig)


def load_config(config_path: Path | None = None) -> AppConfig:
    """
    Carrega a configuração a partir do arquivo TOML.
    Retorna configuração padrão se o arquivo não existir.
    """
    path = config_path or CONFIG_FILE

    if not path.exists():
        return AppConfig()

    with open(path, "rb") as f:
        data = tomllib.load(f)

    geral_data = data.get("geral", {})
    busca_data = data.get("busca", {})
    interface_data = data.get("interface", {})
    nuvem_data = data.get("nuvem", {})

    geral = GeralConfig(
        leitor=geral_data.get("leitor", "zathura"),
        fechar_apos_abrir=geral_data.get("fechar_apos_abrir", True),
    )

    # Suporte a profundidade separada (fallback para profundidade_maxima se existir)
    prof_fallback = busca_data.get("profundidade_maxima", 5)
    
    nuvens_nativas = []
    
    if sys.platform == "win32":
        default_busca_dirs = ["~/Documents", "~/Downloads"]
        default_ignore = [".cache", "node_modules", ".git", "AppData", "Local Settings"]
        
        # Identificação Ocorrente de Nuvens Nativas Windows (OneDrive/GDrive)
        # Tenta pegar todas as variaveis possiveis de OneDrive
        for od_key in ["OneDrive", "OneDriveConsumer", "OneDriveCommercial"]:
            od_val = os.environ.get(od_key)
            if od_val and Path(od_val).exists() and od_val not in nuvens_nativas:
                nuvens_nativas.append(od_val)
                
        # Busca física (Fallbacks)
        userprofile = os.environ.get("USERPROFILE", "")
        if userprofile:
            od_base = Path(userprofile) / "OneDrive"
            if od_base.exists() and str(od_base) not in nuvens_nativas:
                nuvens_nativas.append(str(od_base))
            
            # Empresas (OneDrive - NomeDaEmpresa)
            import glob
            for match in glob.glob(str(Path(userprofile) / "OneDrive - *")):
                if str(match) not in nuvens_nativas:
                    nuvens_nativas.append(str(match))
            
        gdrive_paths = ["G:\\My Drive", os.path.expanduser("~/Google Drive")]
        for gdir in gdrive_paths:
            if Path(gdir).exists() and gdir not in nuvens_nativas:
                nuvens_nativas.append(gdir)
    else:
        default_busca_dirs = ["~/Documentos", "~/Downloads"]
        default_ignore = [".cache", "node_modules", ".git"]

    # Mesclar com as configurações do usuário sem duplicatas
    user_dirs = busca_data.get("diretorios", default_busca_dirs)
    if sys.platform == "win32":
        for default_dir in default_busca_dirs:
            if default_dir not in user_dirs:
                user_dirs.append(default_dir)
        # Importante: garantir que as nuvens nativas descobertas agora tb facam parte dos dirs de busca
        for n in nuvens_nativas:
            if n not in user_dirs:
                user_dirs.append(n)

    busca = SearchConfig(
        diretorios=user_dirs,
        profundidade_local=busca_data.get("profundidade_local", prof_fallback),
        profundidade_nuvem=busca_data.get("profundidade_nuvem", 15),
        ignorar=busca_data.get("ignorar", default_ignore),
        prefixo_nuvem=busca_data.get("prefixo_nuvem", "~/Nuvem"),
        diretorios_nuvem_nativa=nuvens_nativas
    )

    interface = InterfaceConfig(
        largura=interface_data.get("largura", 620),
        max_resultados=interface_data.get("max_resultados", 12),
    )

    nuvem = CloudConfig(
        auto_montar=nuvem_data.get("auto_montar", False),
        remotes=nuvem_data.get("remotes", {}),
    )

    return AppConfig(geral=geral, busca=busca, interface=interface, nuvem=nuvem)
