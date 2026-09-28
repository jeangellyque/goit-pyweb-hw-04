import json
import logging
import mimetypes
import socket
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parent
STORAGE_DIR = ROOT / "storage"
DATA_FILE = STORAGE_DIR / "data.json"
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 3000
UDP_HOST = "127.0.0.1"
UDP_PORT = 5000


class RequestHandler(BaseHTTPRequestHandler):
    def _send_file(self, path: Path, status: int = 200) -> None:
        content = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_not_found(self) -> None:
        self._send_file(ROOT / "error.html", status=404)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        pages = {
            "/": ROOT / "index.html",
            "/index.html": ROOT / "index.html",
            "/message.html": ROOT / "message.html",
            "/style.css": ROOT / "style.css",
            "/logo.png": ROOT / "logo.png",
        }
        file_path = pages.get(path)
        if file_path is None:
            self._send_not_found()
            return
        self._send_file(file_path)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/message":
            self._send_not_found()
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        try:
            form = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        except UnicodeDecodeError:
            self.send_error(400, "Form data must be UTF-8")
            return

        message = {
            "username": form.get("username", [""])[0],
            "message": form.get("message", [""])[0],
        }
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
                udp_socket.sendto(
                    json.dumps(message, ensure_ascii=False).encode("utf-8"),
                    (UDP_HOST, UDP_PORT),
                )
        except OSError:
            self.send_error(502, "Could not forward message to storage server")
            return

        self.send_response(303)
        self.send_header("Location", "/message.html")
        self.send_header("Content-Length", "0")
        self.end_headers()


def run_udp_server(ready: threading.Event) -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("{}\n", encoding="utf-8")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_server:
        udp_server.bind((UDP_HOST, UDP_PORT))
        ready.set()
        logging.info("UDP server listening on %s:%s", UDP_HOST, UDP_PORT)

        while True:
            data, _ = udp_server.recvfrom(65507)
            try:
                message = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                logging.error("Ignoring invalid UDP message: %s", error)
                continue

            if not isinstance(message, dict):
                logging.error("Ignoring UDP message that is not a dictionary")
                continue

            messages = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            if not isinstance(messages, dict):
                raise ValueError(f"{DATA_FILE} must contain a JSON object")
            messages[datetime.now().isoformat(sep=" ")] = message
            DATA_FILE.write_text(
                json.dumps(messages, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    udp_ready = threading.Event()
    udp_thread = threading.Thread(
        target=run_udp_server, args=(udp_ready,), name="udp-server", daemon=True
    )
    udp_thread.start()
    if not udp_ready.wait(timeout=5):
        raise RuntimeError("UDP server did not start within 5 seconds")

    http_server = ThreadingHTTPServer((HTTP_HOST, HTTP_PORT), RequestHandler)
    logging.info("HTTP server listening on %s:%s", HTTP_HOST, HTTP_PORT)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down HTTP server")
    finally:
        http_server.server_close()


if __name__ == "__main__":
    main()
