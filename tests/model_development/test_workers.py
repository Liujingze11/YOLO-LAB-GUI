import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
import tempfile
import time
import unittest
from pathlib import Path
from PyQt5.QtWidgets import QApplication


class WorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def worker(self, command):
        try:
            from yolo_backprop.model_development.gui.workers import ToolWorker
        except ModuleNotFoundError as exc:
            self.fail('Managed PyQt5 workers are not implemented: '+str(exc))
        return ToolWorker(command)

    def test_cancel_silent_process_is_nonblocking_and_cleans_children(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp)/'pids'
            script = "import subprocess,sys,time,os; c=subprocess.Popen([sys.executable,'-c','import time;time.sleep(90)']); open(sys.argv[1],'w').write(str(os.getpid())+' '+str(c.pid)); time.sleep(90)"
            worker = self.worker([sys.executable, '-u', '-c', script, str(marker)])
            stopped = []; failed = []; worker.stopped.connect(lambda: stopped.append(True)); worker.failed.connect(failed.append)
            worker.start()
            try:
                deadline = time.monotonic() + 8
                while not marker.exists() and time.monotonic() < deadline:
                    self.app.processEvents(); time.sleep(.02)
                self.assertTrue(marker.exists(), 'actual child process started')
                pids = [int(p) for p in marker.read_text().split()]
                start = time.monotonic(); worker.stop()
                self.assertLess(time.monotonic() - start, .2)
                self.assertTrue(worker.wait(8000)); self.app.processEvents()
                self.assertTrue(stopped); self.assertFalse(failed)
                for pid in pids:
                    proc = Path(f'/proc/{pid}/stat')
                    try: state = proc.read_text().split()[2]
                    except FileNotFoundError: state = 'gone'
                    self.assertIn(state, ['gone', 'Z'], f'process {pid} still running')
                self.assertTrue(worker._process.stdout.closed, 'worker closes its owned log pipe')
            finally:
                worker.stop(); worker.wait(8000)

    def test_stop_before_start_never_launches_a_command(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp)/'started'
            worker = self.worker([sys.executable, '-c', 'import pathlib,sys;pathlib.Path(sys.argv[1]).touch()', str(marker)])
            worker.stop(); worker.start(); self.assertTrue(worker.wait(5000))
            self.assertFalse(marker.exists())

    def test_leader_exit_does_not_hang_on_a_descendant_log_pipe(self):
        import signal
        script = "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time;time.sleep(90)'])"
        worker = self.worker([sys.executable, '-c', script])
        worker.start()
        try:
            self.assertTrue(worker.wait(3000), 'worker should clean up descendants after its leader exits')
        finally:
            if worker.isRunning() and worker._process:
                try: os.killpg(worker._process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                worker.wait(5000)
