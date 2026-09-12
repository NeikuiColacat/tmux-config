# tmux-config

个人 Linux / WSL / SSH tmux 配置：Catppuccin Latte 浅色主题、Vim 风格操作、CPU / 内存状态、Codex 完成铃声支持。无需 TPM 或第三方 Python 包。

## 新服务器安装

要求：Linux、tmux **3.2+**、Python **3.8+**，以及 `tmux-256color` terminfo。当前实际验证环境为 tmux 3.4、Python 3.12、Windows Terminal 1.24。

Ubuntu / Debian 安装依赖（有管理员权限时执行）：

```bash
sudo apt update
sudo apt install -y tmux git python3 ncurses-bin ncurses-term
```

依赖已安装后，以自己的普通用户运行：

```bash
git clone https://github.com/NeikuiColacat/tmux-config.git ~/.local/share/tmux-config
cd ~/.local/share/tmux-config
./install.sh --terminal windows-terminal
tmux new -A -s main
```

`windows-terminal` 适合从 **Windows Terminal 1.24+** 直接使用 WSL，或通过 SSH 连接服务器；它声明真彩色和同步刷新能力。使用其他客户端时运行 `./install.sh --terminal auto`，避免强制声明同步刷新。基础配置假定外层 `xterm-256color` 客户端支持真彩色。

已经配置 GitHub SSH 密钥的机器也可以用：

```bash
git clone git@github.com:NeikuiColacat/tmux-config.git ~/.local/share/tmux-config
```

安装脚本不调用 sudo、不安装软件、不修改 shell 启动文件、不自动重启或重载现有 tmux。没有管理员权限时，先请管理员安装依赖，或使用已有的用户级 tmux。旧发行版若提供 tmux 3.0，需先升级到满足要求的版本。

## 安装内容与更新

| 路径 | 用途 |
| --- | --- |
| `~/.tmux.conf` | 完整配置，由仓库模板生成 |
| `~/.config/tmux-config/scripts/system-stats.py` | CPU / 内存采样 |
| `~/.config/tmux-config/terminal.conf` | 终端能力 profile |
| `~/.tmux.conf.local` | 可选本机覆盖，安装脚本不会改写 |
| `~/.local/state/tmux-config/backups/` | 每次有变更时自动备份原文件 |
| `${XDG_CACHE_HOME:-~/.cache}/tmux-config/` | 按主机区分的短期采样缓存 |

仓库里的 `tmux.conf` 含安装路径占位符，请通过 `install.sh` 安装，不要直接复制模板。脚本会用独立 tmux socket 检查配置，不会操作现有会话。

之后更新：

```bash
cd ~/.local/share/tmux-config
git pull --ff-only
./install.sh
```

未指定 `--terminal` 时会保留已经安装的 profile；首次安装默认为 `auto`。文件内容未变时不重写、不创建新备份。

在 tmux 中按 **Ctrl+B，然后 R** 重载。终端能力变化后，按 **Ctrl+B，然后 D** 脱离，再执行 `tmux attach`；窗格里的程序会继续运行。不要为了重载配置执行 `tmux kill-server`。

若只能写入某个工作目录，可指定：

```bash
./install.sh --target-home /mnt/workspace/your-user --terminal windows-terminal
tmux -f /mnt/workspace/your-user/.tmux.conf new -A -s main
```

自定义目录不会改变 shell 的 HOME；应在 tmux server 首次启动时使用 `-f` 指定配置。已有 server 使用其启动时的配置，需要手动 `source-file` 或使用独立的 `-L` socket。

恢复时，从对应备份目录把旧的 `.tmux.conf` 和 `.config/tmux-config/` 中的文件复制回原位置，再重载。备份只包含被替换的旧文件；本机覆盖文件始终保留。

## 右下角 CPU / 内存

右下角只显示 CPU 和内存，例如 `CPU 12% MEM 34%`。

- **CPU**：`/proc/stat` 全部逻辑 CPU 的平均利用率，范围 0–100%，不是负载均值。按两次采样的计数差计算；idle 和 iowait 视为空闲，guest 时间不重复累加。
- **MEM**：`(MemTotal - MemAvailable) / MemTotal`，避免把所有可回收缓存都算成内存压力。
- **范围**：运行 tmux 的 Linux 主机。SSH 时是服务器，WSL 时是 WSL 虚拟机；不表示 Windows 全系统、当前进程或容器的 cgroup 配额。
- 状态栏定时更新为 **15 秒**，不是后台常驻监控。5 秒内的重复绘制复用缓存；首次 CPU 采样等待 0.1 秒，tmux 以异步状态栏任务运行它。
- 多个 tmux server 的采样通过文件锁协调，重启后会重新采样；指标不可读取时显示 `--%`。

可单独检查：

```bash
python3 ~/.config/tmux-config/scripts/system-stats.py
```

计算口径参考 [Linux 内核 /proc 文档](https://www.kernel.org/doc/html/latest/filesystems/proc.html)。

## 常用操作

`前缀` 指先按 `Ctrl+B`、松开，再按后面的键；大小写区分。

| 快捷键 | 操作 |
| --- | --- |
| 前缀 `c` | 在当前目录创建窗口 |
| 前缀 `\|` / `-` | 左右 / 上下分屏 |
| 前缀 `h j k l` | 切换窗格 |
| 前缀 `H J K L` | 调整窗格大小，可连续按 |
| `Alt+左` / `Alt+右` | 切换窗口，无需前缀 |
| 前缀 `<` / `>` | 交换窗格 |
| 前缀 `z` | 放大 / 恢复当前窗格 |
| 前缀 `[` | 进入回滚 / 复制模式 |
| 复制模式 `v` → 移动 → `y` | 选择并复制 |
| 前缀 `]` | 粘贴 tmux 缓冲区 |
| 前缀 `r` | 重载配置 |
| 前缀 `d` | 脱离，程序继续运行 |

保留默认 `Ctrl+B` 前缀、鼠标、焦点事件和 50,000 行历史。复制到本机系统剪贴板还取决于终端的 OSC 52 支持。`Alt+左右` 已被 tmux 占用，窗格内的 Codex / shell 不会收到这两个按键。

例如取消这两个直接绑定，可在 `~/.tmux.conf.local` 中写入：

```tmux
unbind -n M-Left
unbind -n M-Right
```

## Catppuccin Latte 与 Codex

tmux 使用 Latte 配色，但它不会给整个终端改主题。Windows Terminal 请使用 [Catppuccin 官方适配](https://github.com/catppuccin/windows-terminal)：

1. 把官方 `latte.json` 对象加入 Windows Terminal 的 `schemes` 数组。
2. 把官方 `latteTheme.json` 对象加入 `themes` 数组。
3. 将使用的 profile 的 `colorScheme` 设为 `Catppuccin Latte`；将顶层 `theme` 也设为 `Catppuccin Latte`。
4. 将 profile 的 `bellStyle` 设为 `audible`，以播放终端铃声。

服务器安装脚本不会修改 Windows Terminal、Neovim 或 Codex 的配置。需要 Codex Latte 高亮和完成通知时，把 [examples/codex-tui.toml](examples/codex-tui.toml) 的字段合并到 `~/.codex/config.toml` **已有的 `[tui]` 表**，不要复制覆盖整个文件，也不要创建第二个 `[tui]` 表。重启 Codex 后生效。

Codex 的 `tui.theme` 控制代码语法高亮，动画由 `tui.animations` 控制；完成通知通过终端 BEL 传输。参考 [Codex 配置文档](https://developers.openai.com/codex/config-reference/)。

测试终端声音：

```bash
printf '\a'
```

前后台窗口都可转发铃声，发生铃声的窗口名后会有 `!`。SSH 断开且没有连接客户端时，终端铃声无法传回本机。

## 性能与验证

保持 15 秒状态栏更新，减少高频启动监控命令。大量日志优先写文件按需查看；历史限制按行数计算，少量很长的行也可能占用较多内存，调整 `history-limit` 只影响新建窗格。

`sync` profile 控制 tmux 向外层终端输出的同步刷新；tmux 3.7 才加入对窗格内应用发送 DECSET 2026 的支持。二者不同，3.4 启用 profile 不等于升级了应用侧支持。参考 [tmux 更新记录](https://github.com/tmux/tmux/blob/3.7b/CHANGES)。

仓库测试使用合成 CPU / 内存数据、临时安装目录和独立 tmux server：

```bash
python3 -m unittest discover -s tests -v
```

把本仓库链接交给新会话中的助手，并要求“读取 README，按 Windows Terminal profile 安装本仓库”，即可按相同要求配置新的 Linux 服务器。
