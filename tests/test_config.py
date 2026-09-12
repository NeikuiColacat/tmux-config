import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stats", ROOT / "scripts/system-stats.py")
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


class MetricsTests(unittest.TestCase):
    def test_cpu_guest_not_double_counted_and_iowait_idle(self):
        # 100 user + 100 system + 700 idle + 100 iowait; guest already in user.
        counters = stats.cpu_counters("cpu 100 0 100 700 100 0 0 0 50 0\n")
        self.assertEqual(counters, (1000, 800))
        self.assertEqual(stats.cpu_percent((0, 0), counters), 20)

    def test_cpu_delta_and_counter_reset(self):
        self.assertEqual(stats.cpu_percent((1000, 800), (1200, 850)), 75)
        self.assertIsNone(stats.cpu_percent((1200, 850), (100, 80)))
        self.assertIsNone(stats.cpu_percent((1000, 800), (1000, 800)))
        self.assertIsNone(stats.cpu_percent((1000, 800), (1200, 790)))

    def test_memory_uses_available_not_free(self):
        text = "MemTotal: 1000 kB\nMemFree: 10 kB\nMemAvailable: 750 kB\n"
        self.assertEqual(stats.memory_percent(text), 25)
        self.assertIsNone(stats.memory_percent("MemTotal: 1000 kB\nMemFree: 10 kB\n"))

    def test_sample_cache_delta_reboot_and_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            proc = root / "proc"
            (proc / "sys/kernel/random").mkdir(parents=True)
            (proc / "sys/kernel/random/boot_id").write_text("test-boot")
            (proc / "stat").write_text("cpu 300 0 100 900 100 0 0 0 20 0\n")
            (proc / "meminfo").write_text("MemTotal: 1000 kB\nMemAvailable: 600 kB\n")
            cache = root / "cache"
            cache.mkdir()
            old = dict(boot_id="test-boot", time=time.monotonic() - 15,
                       counters=[1000, 800], cpu=0, memory=1)
            (cache / "stats.json").write_text(json.dumps(old))
            self.assertEqual(stats.sample(cache, proc), "CPU 50% MEM 40%")
            (proc / "stat").write_text("broken\n")
            self.assertEqual(stats.sample(cache, proc), "CPU 50% MEM 40%")
            (proc / "stat").write_text("cpu 300 0 100 900 100 0 0 0 20 0\n")
            (proc / "sys/kernel/random/boot_id").write_text("new-boot")
            self.assertEqual(stats.sample(cache, proc), "CPU --% MEM 40%")
            (cache / "stats.json").write_text("broken JSON")
            self.assertEqual(stats.sample(cache, proc), "CPU --% MEM 40%")


class InstallationTests(unittest.TestCase):
    def install(self, target, *options):
        return subprocess.run([str(ROOT / "install.sh"), "--target-home", str(target), *options],
                              capture_output=True, text=True, check=True)

    def test_backup_local_override_rendering_and_idempotence(self):
        with tempfile.TemporaryDirectory(prefix="tmux-install-test-") as temp:
            target = Path(temp) / "user space"
            target.mkdir()
            (target / ".tmux.conf").write_text("# original configuration\n")
            local = target / ".tmux.conf.local"
            local.write_text("set -g status-interval 20\n")
            self.install(target, "--terminal", "windows-terminal")
            config = (target / ".tmux.conf").read_text()
            self.assertNotIn("@STATUS_RIGHT@", config)
            self.assertIn("system-stats.py", config)
            self.assertIn("source-file -q", config)
            profile = target / ".config/tmux-config/terminal.conf"
            self.assertIn("RGB:sync", profile.read_text())
            backups = list((target / ".local/state/tmux-config/backups").iterdir())
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / ".tmux.conf").read_text(), "# original configuration\n")
            original_mtime = (target / ".tmux.conf").stat().st_mtime_ns
            self.install(target)
            self.assertEqual((target / ".tmux.conf").stat().st_mtime_ns, original_mtime)
            self.assertEqual(local.read_text(), "set -g status-interval 20\n")
            self.assertEqual(len(list(backups[0].parent.iterdir())), 1)
            self.assertIn("RGB:sync", profile.read_text())
            self.install(target, "--terminal", "auto")
            self.assertNotIn("RGB:sync", profile.read_text())

    def test_invalid_local_override_does_not_replace_existing_files(self):
        with tempfile.TemporaryDirectory(prefix="tmux-install-invalid-") as temp:
            target = Path(temp)
            config = target / ".tmux.conf"
            config.write_text("# preserve this\n")
            (target / ".tmux.conf.local").write_text("not-a-tmux-command\n")
            with self.assertRaises(subprocess.CalledProcessError):
                self.install(target)
            self.assertEqual(config.read_text(), "# preserve this\n")
            self.assertFalse((target / ".local/state/tmux-config/backups").exists())


if __name__ == "__main__":
    unittest.main()
