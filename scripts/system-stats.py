#!/usr/bin/env python3
"""Linux/WSL host CPU and RAM percentages; no third-party dependencies."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time


def cpu_counters(text):
    fields = text.splitlines()[0].split()
    if fields[0] != "cpu" or len(fields) < 5:
        raise ValueError("missing aggregate CPU counters")
    values = [int(value) for value in fields[1:9]]
    values += [0] * (8 - len(values))
    # user/nice already include guest/guest_nice: do not add fields 9 and 10.
    return sum(values), values[3] + values[4]


def cpu_percent(before, after):
    total = after[0] - before[0]
    idle = after[1] - before[1]
    if total <= 0 or idle < 0 or idle > total:
        return None
    return round(100 * (total - idle) / total)


def memory_percent(text):
    values = {}
    for line in text.splitlines():
        key, _, value = line.partition(":")
        if key in ("MemTotal", "MemAvailable"):
            values[key] = int(value.split()[0])
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable")
    if total <= 0 or available is None:
        return None
    return round(100 * (total - min(total, max(0, available))) / total)


def format_stats(cpu, memory):
    return "CPU {}% MEM {}%".format(
        "--" if cpu is None else cpu, "--" if memory is None else memory
    )


def sample(cache_dir, proc_root=Path("/proc")):
    cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (cache_dir / "lock").open("w") as lock:
        # Separate tmux servers may request a reading simultaneously.
        fcntl.flock(lock, fcntl.LOCK_EX)
        boot_id = (proc_root / "sys/kernel/random/boot_id").read_text().strip()
        now = time.monotonic()
        cache_file = cache_dir / "stats.json"
        try:
            previous = json.loads(cache_file.read_text())
            assert isinstance(previous, dict)
            assert previous["boot_id"] == boot_id
            assert 0 <= now - previous["time"] < 3600
            assert len(previous["counters"]) == 2
            assert all(type(v) is int and v >= 0 for v in previous["counters"])
            assert all(v is None or (type(v) is int and 0 <= v <= 100)
                       for v in (previous["cpu"], previous["memory"]))
        except (OSError, ValueError, KeyError, TypeError, AssertionError):
            previous = None
        # Merge redraw requests within five seconds; regular status refresh is 15s.
        if previous is not None and now - previous["time"] < 5:
            return format_stats(previous["cpu"], previous["memory"])
        counters = cpu_counters((proc_root / "stat").read_text())
        if previous is None:
            before = counters
            time.sleep(0.1)  # Only the first sample; tmux runs status jobs asynchronously.
            counters = cpu_counters((proc_root / "stat").read_text())
        else:
            before = previous["counters"]
        cpu = cpu_percent(before, counters)
        memory = memory_percent((proc_root / "meminfo").read_text())
        result = dict(boot_id=boot_id, time=time.monotonic(), counters=counters,
                      cpu=cpu, memory=memory)
        fd, name = tempfile.mkstemp(prefix=".stats-", dir=cache_dir)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(result, stream)
            os.replace(name, cache_file)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        return format_stats(cpu, memory)


def main():
    # Host-specific cache also works when HOME is shared over NFS.
    host = hashlib.sha256(os.uname().nodename.encode()).hexdigest()[:16]
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    try:
        print(sample(cache / "tmux-config" / host))
    except (OSError, ValueError, IndexError, TypeError):
        # An unavailable metric must not break or flood the status line.
        print(format_stats(None, None))


if __name__ == "__main__":
    main()
