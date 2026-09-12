#!/usr/bin/env python3
"""Validate, back up and copy the tmux configuration without sudo or auto-reload."""

import argparse
import datetime
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile


def tmux_quote(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$") + '"'


def validate(config):
    # A private socket keeps validation separate from all running user sessions.
    with tempfile.TemporaryDirectory(prefix="tmux-config-check-") as temp:
        staged = Path(temp) / "tmux.conf"
        staged.write_text(config)
        base = ["tmux", "-S", str(Path(temp) / "s")]
        env = os.environ.copy()
        env.pop("TMUX", None)
        try:
            subprocess.run(base + ["-f", "/dev/null", "new-session", "-d",
                                   "-s", "check", "sleep 30"],
                           env=env, check=True, capture_output=True, text=True)
            result = subprocess.run(base + ["source-file", str(staged)],
                                    env=env, capture_output=True, text=True)
            if result.returncode or result.stderr:
                raise RuntimeError(result.stderr.strip() or "tmux config validation failed")
        finally:
            subprocess.run(base + ["kill-server"], env=env, capture_output=True)


def atomic_write(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".tmux-config-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal", choices=("auto", "windows-terminal"),
                        help="omitted: preserve installed profile; first install: auto")
    parser.add_argument("--target-home", type=Path, default=Path.home(),
                        help="install under this directory (default: current user's home)")
    args = parser.parse_args()
    if sys.version_info < (3, 8):
        parser.error("需要 Python 3.8+")
    for command in ("tmux", "infocmp"):
        if shutil.which(command) is None:
            parser.error("缺少 {}；Ubuntu/Debian: apt install tmux ncurses-bin ncurses-term".format(command))
    version = subprocess.check_output(["tmux", "-V"], text=True).strip()
    match = re.search(r"(\d+)\.(\d+)", version)
    if not match or tuple(map(int, match.groups())) < (3, 2):
        parser.error("需要 tmux 3.2+；当前版本: " + version)
    if subprocess.run(["infocmp", "-x", "tmux-256color"],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        parser.error("缺少 tmux-256color terminfo；请安装 ncurses-term 或使用 tic 导入")
    repo = Path(__file__).resolve().parent.parent
    target_home = args.target_home.expanduser().resolve()
    config_dir = target_home / ".config/tmux-config"
    main_config = target_home / ".tmux.conf"
    terminal_config = config_dir / "terminal.conf"
    local_config = target_home / ".tmux.conf.local"
    stats_file = config_dir / "scripts/system-stats.py"
    if args.terminal:
        profile = (repo / "profiles" / (args.terminal + ".conf")).read_text()
    elif terminal_config.exists():
        profile = terminal_config.read_text()
    else:
        profile = (repo / "profiles/auto.conf").read_text()
    stats_command = shlex.join([sys.executable, str(stats_file)])
    status = ("#[fg=#6c6f85,nobold] #(" + stats_command + ") | %Y-%m-%d "
              "#[fg=#4c4f69]%H:%M #[fg=#4c4f69,bg=#dce0e8,bold] #h #[default]")
    config = (repo / "tmux.conf").read_text()
    for token, value in {"MAIN_CONFIG": main_config, "STATUS_RIGHT": status,
                         "TERMINAL_CONFIG": terminal_config, "LOCAL_CONFIG": local_config}.items():
        config = config.replace("@" + token + "@", tmux_quote(value))
    # Validate the selected profile even before it exists in its target directory.
    validation_config = config.replace("source-file -q " + tmux_quote(terminal_config), profile)
    validate(validation_config)
    files = {stats_file: (repo / "scripts/system-stats.py").read_text(),
             terminal_config: profile, main_config: config}
    changed = {p: text for p, text in files.items()
               if p.is_symlink() or not p.exists() or p.read_text() != text}
    if not changed:
        print("配置已是最新，无需修改。")
        return
    state = target_home / ".local/state/tmux-config/backups"
    state.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-")
    backup = Path(tempfile.mkdtemp(prefix=stamp, dir=state))
    for path in changed:
        if path.exists() or path.is_symlink():
            dest = backup / path.relative_to(target_home)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest, follow_symlinks=False)
    for path, content in changed.items():
        atomic_write(path, content)
    print("已安装: " + str(main_config))
    print("原文件备份: " + str(backup))
    print("现有 tmux 中按 Ctrl+B 然后 R 重载；终端能力变化需要 detach/attach。")
    print("不会重启现有会话，也不会修改 Codex 或 Windows Terminal 配置。")
    if target_home != Path.home().resolve():
        print("自定义安装目录，启动时使用: tmux -f " + shlex.quote(str(main_config)))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print("安装失败: " + str(error), file=sys.stderr)
        sys.exit(1)
