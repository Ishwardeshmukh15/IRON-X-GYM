import json
import os
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

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
