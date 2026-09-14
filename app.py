import json
import mimetypes
import os
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

import mysql.connector

ROOT = os.path.dirname(os.path.abspath(__file__))


def load_dotenv():
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv()
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "ironx_gym"),
}


class IronXRequestHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path not in ("/api/signup", "/api/booking"):
            self.send_json({"error": "Endpoint not found."}, 404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length))
        except (ValueError, json.JSONDecodeError):
            self.send_json({"error": "Please send valid form data."}, 400)
            return

        if self.path == "/api/signup":
            email = str(payload.get("email", "")).strip()
            if not email or "@" not in email:
                self.send_json({"error": "Please enter a valid email address."}, 400)
                return
            lead = {"email": email, "created_at": timestamp()}
        else:
            required = ("name", "age", "location", "email", "phone", "height", "weight", "body_type")
            if any(not str(payload.get(field, "")).strip() for field in required):
                self.send_json({"error": "Please complete every booking field."}, 400)
                return
            if "@" not in str(payload["email"]):
                self.send_json({"error": "Please enter a valid email address."}, 400)
                return
            lead = {field: str(payload[field]).strip() for field in required}
            lead["created_at"] = timestamp()

        try:
            save_lead(lead)
        except RuntimeError as error:
            self.send_json({"error": str(error)}, 503)
            return
        self.send_json({"message": "Thanks. The IronX team will be in touch soon."}, 201)

    def send_json(self, payload, status):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


handler = IronXRequestHandler


def app(environ, start_response):
    path = unquote(environ.get("PATH_INFO", "/"))
    method = environ.get("REQUEST_METHOD", "GET").upper()

    if method == "POST" and path in ("/api/signup", "/api/booking"):
        try:
            content_length = int(environ.get("CONTENT_LENGTH", "0"))
            payload = json.loads(environ["wsgi.input"].read(content_length))
        except (ValueError, json.JSONDecodeError):
            return wsgi_json(start_response, {"error": "Please send valid form data."}, 400)

        if path == "/api/signup":
            email = str(payload.get("email", "")).strip()
            if not email or "@" not in email:
                return wsgi_json(start_response, {"error": "Please enter a valid email address."}, 400)
            lead = {"email": email, "created_at": timestamp()}
        else:
            required = ("name", "age", "location", "email", "phone", "height", "weight", "body_type")
            if any(not str(payload.get(field, "")).strip() for field in required):
                return wsgi_json(start_response, {"error": "Please complete every booking field."}, 400)
            if "@" not in str(payload["email"]):
                return wsgi_json(start_response, {"error": "Please enter a valid email address."}, 400)
            lead = {field: str(payload[field]).strip() for field in required}
            lead["created_at"] = timestamp()

        try:
            save_lead(lead)
        except RuntimeError as error:
            return wsgi_json(start_response, {"error": str(error)}, 503)
        return wsgi_json(start_response, {"message": "Thanks. The IronX team will be in touch soon."}, 201)

    if method not in ("GET", "HEAD"):
        return wsgi_text(start_response, "Method not allowed.", 405)

    relative_path = "index.html" if path == "/" else path.lstrip("/")
    file_path = os.path.abspath(os.path.join(ROOT, relative_path))
    if os.path.commonpath((ROOT, file_path)) != ROOT or not os.path.isfile(file_path):
        return wsgi_text(start_response, "Not found.", 404)

    with open(file_path, "rb") as file:
        body = file.read()
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    start_response("200 OK", [("Content-Type", content_type), ("Content-Length", str(len(body)))])
    return [b"" if method == "HEAD" else body]


def wsgi_json(start_response, payload, status):
    body = json.dumps(payload).encode("utf-8")
    start_response(f"{status} {'Created' if status == 201 else 'Bad Request' if status == 400 else 'Service Unavailable'}", [("Content-Type", "application/json"), ("Content-Length", str(len(body))), ("Cache-Control", "no-store")])
    return [body]


def wsgi_text(start_response, body, status):
    encoded_body = body.encode("utf-8")
    reason = "Not Found" if status == 404 else "Method Not Allowed"
    start_response(f"{status} {reason}", [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(encoded_body)))])
    return [encoded_body]


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def save_lead(lead):
    if not MYSQL_CONFIG["password"]:
        raise RuntimeError("MySQL is not configured. Set MYSQL_PASSWORD before starting the server.")

    try:
        with mysql.connector.connect(**MYSQL_CONFIG) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    insert into leads
                    (name, age, location, email, phone, height, weight, body_type, created_at)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        lead.get("name"),
                        int(lead["age"]) if lead.get("age") else None,
                        lead.get("location"),
                        lead["email"],
                        lead.get("phone"),
                        lead.get("height"),
                        lead.get("weight"),
                        lead.get("body_type"),
                        lead["created_at"],
                    ),
                )
            connection.commit()
    except (mysql.connector.Error, ValueError) as error:
        raise RuntimeError("MySQL could not save the booking. Check the server, password, and schema.") from error


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 5500), IronXRequestHandler)
    print("IronX Gym running at http://127.0.0.1:5500")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping IronX Gym server")
    finally:
        server.server_close()
