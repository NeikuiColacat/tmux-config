# 维护约定

- 先读取 README.md。保留 Catppuccin Latte、Ctrl+B 前缀、现有快捷键、15 秒状态更新和完成铃声。
- tmux.conf 是安装模板，由 install.sh 渲染用户路径。不要写入个人绝对路径、主机地址、密钥、Codex 账户或完整 Codex 配置。
- 安装只写当前用户目录，先校验、再备份；保留 .tmux.conf.local 和运行中的 tmux 会话。
- CPU / MEM 指标表示运行 tmux 的 Linux 主机；不要把 load average 写成 CPU 利用率，也不要用 MemFree 代替 MemAvailable。
- 不因终端 TERM 名含 256color 就推断它支持同步刷新；Windows Terminal profile 是显式选择。
- 修改安装器或采样逻辑后运行 README 中的测试。tmux 测试使用独立 socket，不得结束用户的默认 server。
