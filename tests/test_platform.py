"""
Filebrowser — Testes da Abstração de Plataforma (platform.py)

Testa o singleton e as implementações sem dependência de GUI.
"""

from src.platform import platform, LinuxPlatform, WindowsPlatform


# ─── Singleton ───────────────────────────────────────────────────────────────


def test_platform_singleton_exists():
    assert platform is not None


def test_platform_is_linux_or_windows():
    assert isinstance(platform, (LinuxPlatform, WindowsPlatform))


# ─── is_windows ──────────────────────────────────────────────────────────────


def test_platform_is_windows_matches_sys():
    import sys
    expected = (sys.platform == "win32")
    assert platform.is_windows == expected


def test_linux_platform_is_windows_false():
    p = LinuxPlatform()
    assert p.is_windows is False


def test_windows_platform_is_windows_true():
    p = WindowsPlatform()
    assert p.is_windows is True


# ─── get_default_dirs ────────────────────────────────────────────────────────


def test_get_default_dirs_returns_list():
    dirs = platform.get_default_dirs()
    assert isinstance(dirs, list)
    assert len(dirs) > 0


def test_get_default_dirs_all_strings():
    for d in platform.get_default_dirs():
        assert isinstance(d, str)


# ─── get_default_ignore ──────────────────────────────────────────────────────


def test_get_default_ignore_returns_list():
    ign = platform.get_default_ignore()
    assert isinstance(ign, list)
    assert len(ign) > 0


# ─── get_config_dirs ─────────────────────────────────────────────────────────


def test_get_config_dirs_returns_tuple():
    config_dir, cache_dir = platform.get_config_dirs()
    assert config_dir is not None
    assert cache_dir is not None


# ─── detect_wm ───────────────────────────────────────────────────────────────


def test_detect_wm_returns_string():
    wm = platform.detect_wm()
    assert isinstance(wm, str)
    assert len(wm) > 0


# ─── detect_native_clouds ───────────────────────────────────────────────────


def test_detect_native_clouds_returns_list():
    clouds = platform.detect_native_clouds()
    assert isinstance(clouds, list)


# ─── get_extra_disk_paths ───────────────────────────────────────────────────


def test_get_extra_disk_paths_returns_list():
    paths = platform.get_extra_disk_paths()
    assert isinstance(paths, list)
