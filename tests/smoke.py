"""Verify the packaged UI and its configurable management proxy."""
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def request(url, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=3) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


source = f"ocidir://{Path(sys.argv[1]).resolve()}:{sys.argv[2] if len(sys.argv) > 2 else 'ci'}"
for arch in ("amd64", "arm64"):
    name = f"ui-smoke-{uuid.uuid4().hex[:10]}"
    containers = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        archive = root / "image.tar"
        image = f"management-ui-smoke:{arch}"
        run("regctl", "image", "export", source, str(archive), "--platform", f"linux/{arch}", "--name", image)
        run("docker", "load", "-i", str(archive))
        config = root / "mock.conf"
        config.write_text('''pid /tmp/nginx.pid;
events {}
http {
 access_log off;
 client_body_temp_path /tmp/client_temp;
 proxy_temp_path /tmp/proxy_temp;
 fastcgi_temp_path /tmp/fastcgi_temp;
 uwsgi_temp_path /tmp/uwsgi_temp;
 scgi_temp_path /tmp/scgi_temp;
 server {
  listen 8182;
  location /v0/resource/plugins/ {
   return 200 '<html>plugin quota page</html>';
  }
  location /v0/management/ {
   if ($http_authorization != "Bearer fixture-key") { return 401; }
   return 200 '{"ok":true}';
  }
 }
}
''')
        run("docker", "network", "create", name)
        try:
            common = ("docker", "run", "-d", "--platform", f"linux/{arch}", "--network", name,
                      "--read-only", "--tmpfs", "/tmp", "--cap-drop", "ALL",
                      "--security-opt", "no-new-privileges:true")
            containers.append(run(*common, "--network-alias", "backend", "-v", f"{config}:/mock.conf:ro",
                                  "--entrypoint", "nginx", image, "-c", "/mock.conf", "-g", "daemon off;"))
            containers.append(run(*common, "-p", "127.0.0.1::8181", "-e", "CLIPROXYAPI_UI_SERVER_PORT=8181",
                                  "-e", "CLIPROXYAPI_UI_API_ENDPOINT=http://backend:8182", image))
            address = run("docker", "port", containers[-1], "8181/tcp")
            base = f"http://{address}"
            for attempt in range(40):
                try:
                    status, body = request(base)
                    if status == 200:
                        break
                except (OSError, urllib.error.URLError):
                    pass
                time.sleep(0.5)
            else:
                raise AssertionError("UI did not start")
            assert b"<html" in body.lower()
            endpoint = base + "/v0/management/config"
            assert request(endpoint)[0] == 401
            assert request(endpoint, "wrong-key")[0] == 401
            status, body = request(endpoint, "fixture-key")
            assert status == 200 and json.loads(body) == {"ok": True}
            status, body = request(base + "/v0/resource/plugins/example/quota")
            assert status == 200 and body == b"<html>plugin quota page</html>"
            quota = base + "/v0/management/plugins/example/quota-usage"
            assert request(quota)[0] == 401
            assert request(quota, "fixture-key")[0] == 200
            assert request(base + "/v0/resource/unrelated")[0] == 404
            assert request(base + "/v1/models")[0] == 404
            print(f"linux/{arch}: UI, proxy configuration, and authentication passed")
        finally:
            for container in reversed(containers):
                run("docker", "rm", "-f", container)
            run("docker", "network", "rm", name)
