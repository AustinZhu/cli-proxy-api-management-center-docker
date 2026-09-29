# CLI Proxy API Management Center Docker

A small container image for the upstream
[CLI Proxy API Management Center](https://github.com/router-for-me/Cli-Proxy-API-Management-Center).
Nginx serves the pinned UI release and forwards management requests to your
CLIProxyAPI backend, so the UI's default server address works without adjustment.
This is independent container packaging, not the upstream application's source.

## Run

```yaml
services:
  management-ui:
    image: ghcr.io/austinzhu/cli-proxy-api-management-center:1.24.2-3
    environment:
      CLIPROXYAPI_UI_API_ENDPOINT: http://cliproxyapi:8317
      CLIPROXYAPI_UI_SERVER_PORT: "8080"
    ports:
      - "127.0.0.1:8788:8080"
    read_only: true
    tmpfs:
      - /tmp:mode=1777
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
    init: true
```

Connect this service to the same Docker network as your existing `cliproxyapi`
backend. Open `http://127.0.0.1:8788` and enter the backend's management key.
The backend must permit management requests from the container network and
require a strong, separate management key. An inference API key is not sufficient.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `CLIPROXYAPI_UI_API_ENDPOINT` | `http://cliproxyapi:8317` | Backend origin without a path or trailing slash |
| `CLIPROXYAPI_UI_SERVER_PORT` | `8080` | Internal HTTP port; update the published port mapping if changed |

`/v0/management/` and `/v0/resource/plugins/` are forwarded. The latter serves
plugin pages and assets; management operations still require the browser's
management credential. Inference requests belong on the backend's own endpoint.
The browser supplies the management credential; the container receives no credentials and does not mount provider token storage. Avoid saving
management credentials in a shared browser profile. Upstream browser storage
obfuscation is not encryption.

The image runs as UID/GID 65534 and supports a read-only filesystem with writable
`/tmp`. Nginx access logging is disabled. Docker's embedded DNS resolves the
backend on a user-defined network. The published image supports AMD64 and ARM64.

## Build and release

```bash
docker build -t management-ui:local .
```

The Dockerfile pins the base image digest and the upstream HTML checksum.
`UI-LICENSE` retains the upstream MIT notice. Update the UI URL, checksum and
license together when upgrading. The explicit libexpat patch addresses a known
vulnerability in the pinned base; remove it when an updated base includes the fix.

CI builds both architectures, scans each exported OCI image, and tests configurable
ports, backend forwarding and authentication with a fake backend. Publication
copies the audited artifact without rebuilding. SBOM and provenance attestations
are included. The scan fails for fixable HIGH/CRITICAL vulnerabilities and secret
findings; scanning bundled JavaScript is not a substitute for a source audit.

Push a version tag such as `v1.24.2-3` to publish the corresponding GitHub
Container Registry tag.
The workflow uses the built-in `GITHUB_TOKEN`; no registry secret is required.
Pull requests and pushes to `main` build and verify without publishing.
Prefer digest-pinned image
references for deployments.

## License

Container packaging is MIT licensed. The upstream UI is separately covered by
its MIT license in `UI-LICENSE`; the base image retains its own component licenses.
