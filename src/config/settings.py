"""
Filebrowser — Módulo de Configuração

Carrega e gerencia as configurações da aplicação a partir do config.toml.
"""

import tomllib
from pathlib import Path
from dataclasses import dataclass, field


__version__ = "0.2.0"

# Caminho raiz do projeto (dois níveis acima de src/config/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Config: ~/.config/filebrowser/ (instalado) ou diretório do projeto (dev)
USER_CONFIG_DIR = Path.home() / ".config" / "filebrowser"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.toml"
PROJECT_CONFIG_FILE = PROJECT_ROOT / "config.toml"

# Usar config do usuário se existir, senão o do projeto
CONFIG_FILE = USER_CONFIG_FILE if USER_CONFIG_FILE.exists() else PROJECT_CONFIG_FILE

CACHE_DIR = Path.home() / ".cache" / "filebrowser"
DB_PATH = CACHE_DIR / "index.db"


@dataclass
class SearchConfig:
    """Configurações de busca."""
    diretorios: list[str] = field(default_factory=lambda: ["~/Documentos", "~/Downloads"])
    profundidade_local: int = 5
    profundidade_nuvem: int = 15
    ignorar: list[str] = field(default_factory=lambda: [".cache", "node_modules", ".git"])
    prefixo_nuvem: str = "~/Nuvem"

    @property
    def diretorios_expandidos(self) -> list[Path]:
        """Retorna os diretórios de busca com ~ expandido e como Path."""
        paths = []
        for d in self.diretorios:
            p = Path(d).expanduser().resolve()
            if p.exists() and p.is_dir():
                paths.append(p)
        return paths

    @property
    def diretorios_locais(self) -> list[Path]:
        """Retorna apenas os diretórios locais (não-nuvem)."""
        nuvem = Path(self.prefixo_nuvem).expanduser().resolve()
        return [p for p in self.diretorios_expandidos if not str(p).startswith(str(nuvem))]

    @property
    def diretorios_nuvem(self) -> list[Path]:
        """Retorna apenas os diretórios de nuvem (rclone)."""
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
    busca = SearchConfig(
        diretorios=busca_data.get("diretorios", ["~/Documentos", "~/Downloads"]),
        profundidade_local=busca_data.get("profundidade_local", prof_fallback),
        profundidade_nuvem=busca_data.get("profundidade_nuvem", 15),
        ignorar=busca_data.get("ignorar", [".cache", "node_modules", ".git"]),
        prefixo_nuvem=busca_data.get("prefixo_nuvem", "~/Nuvem"),
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
