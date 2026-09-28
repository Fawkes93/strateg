"""Stop must kill the sweep process group and leave this process running."""

import os
import time
from multiprocessing import get_context

from backtest.batch import _hold_process_group, _kill_sweep_process


def test_kill_sweep_group_leaves_the_parent_alive():
    ctx = get_context("spawn")
    proc = ctx.Process(target=_hold_process_group, args=(30,))
    proc.start()
    deadline = time.time() + 5
    while time.time() < deadline and proc.is_alive() and proc.pid == os.getpgrp():
        time.sleep(0.05)
    assert proc.pid != os.getpgrp()
    _kill_sweep_process(proc, proc.pid)
    proc.join(timeout=2)
    assert not proc.is_alive()
    assert os.getpid() > 0


def test_kill_refuses_the_server_process_group():
    _kill_sweep_process(None, os.getpgrp())
    assert os.getpid() > 0
