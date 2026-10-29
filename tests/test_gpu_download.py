"""Exercise GPU release discovery and installation against a local HTTP server."""
import io
import json
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from gui.gpu_manager import GpuDownloadWorker


@pytest.fixture
def release_server():
    routes = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            status, content = routes.get(self.path, (404, b'{"message":"Not Found"}'))
            self.send_response(status)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", routes
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def run_download(release_url: str, dest: Path):
    worker = GpuDownloadWorker(release_url, dest)
    results = []
    worker.finished.connect(lambda success, message: results.append((success, message)))
    worker.run()
    assert len(results) == 1
    return results[0]


def test_installs_gpu_asset_discovered_from_release(release_server, tmp_path):
    base_url, routes = release_server
    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("torch/component.txt", "CUDA component fixture")
    routes["/release"] = (200, json.dumps({"assets": [
        {"name": "installer.exe", "browser_download_url": base_url + "/unused"},
        {"name": "gpu_bundle.zip", "browser_download_url": base_url + "/bundle"},
    ]}).encode())
    routes["/bundle"] = (200, bundle.getvalue())
    dest = tmp_path / "gpu"

    success, message = run_download(base_url + "/release", dest)

    assert success, message
    assert (dest / "torch/component.txt").read_text() == "CUDA component fixture"
    assert json.loads((dest / "gpu_ready.json").read_text())["cuda_version"] == "cu121"
    assert not (dest / "gpu_bundle.zip").exists()
    assert not (dest / "gpu_bundle.zip.tmp").exists()


@pytest.mark.parametrize("release_exists", [False, True])
def test_unpublished_gpu_asset_gives_actionable_message(release_server, tmp_path, release_exists):
    base_url, routes = release_server
    if release_exists:
        routes["/release"] = (200, b'{"assets":[]}')
    dest = tmp_path / "gpu"

    success, message = run_download(base_url + "/release", dest)

    assert not success
    assert "YOLO-LAB-GUI" in message
    assert "CPU" in message
    assert not (dest / "gpu_ready.json").exists()
    assert not (dest / "gpu_bundle.zip.tmp").exists()


def test_failed_asset_download_does_not_mark_gpu_ready(release_server, tmp_path):
    base_url, routes = release_server
    routes["/release"] = (200, json.dumps({"assets": [
        {"name": "gpu_bundle.zip", "browser_download_url": base_url + "/broken-bundle"},
    ]}).encode())
    routes["/broken-bundle"] = (503, b"temporarily unavailable")
    dest = tmp_path / "gpu"

    success, message = run_download(base_url + "/release", dest)

    assert not success
    assert "503" in message
    assert not (dest / "gpu_ready.json").exists()
    assert not (dest / "gpu_bundle.zip.tmp").exists()
