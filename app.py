import json
import hashlib
import mimetypes
import os
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal
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
ADMIN_EMAIL = os.environ.get("IRONX_ADMIN_EMAIL", "admin@ironxgym.com")
ADMIN_PASSWORD = os.environ.get("IRONX_ADMIN_PASSWORD", "")
SESSIONS = {}


class IronXRequestHandler(SimpleHTTPRequestHandler):
    def do_DELETE(self):
        if not is_admin(get_session(self)):
            self.send_json({"error": "Admin login required."}, 401)
            return
        parts = self.path.strip("/").split("/")
        if len(parts) != 4 or parts[:2] != ["api", "admin"] or parts[2] not in ("users", "products"):
            self.send_json({"error": "Endpoint not found."}, 404)
            return
        try:
            record_id = int(parts[3])
            table = parts[2]
            db_query(f"delete from {table} where id = %s", (record_id,), commit=True)
        except (ValueError, RuntimeError):
            self.send_json({"error": "Invalid record."}, 400)
            return
        self.send_json({"message": "Record deleted."}, 200)

    def do_POST(self):
        if self.path not in ("/api/signup", "/api/booking", "/api/register", "/api/login", "/api/admin/login", "/api/logout", "/api/profile", "/api/orders", "/api/admin/products", "/api/admin/users", "/api/admin/orders"):
            self.send_json({"error": "Endpoint not found."}, 404)
            return

        payload = {}
        if self.path != "/api/logout":
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(content_length))
            except (ValueError, json.JSONDecodeError):
                self.send_json({"error": "Please send valid form data."}, 400)
                return

        session = get_session(self)
        if self.path == "/api/register":
            try:
                user = register_user(payload)
            except RuntimeError as error:
                self.send_json({"error": str(error)}, 400)
                return
            self.set_session(user["id"], "user")
            self.send_json({"user": public_user(user)}, 201)
            return
        if self.path == "/api/login":
            user = authenticate_user(payload)
            if not user:
                self.send_json({"error": "Email or password is incorrect."}, 401)
                return
            self.set_session(user["id"], "user")
            self.send_json({"user": public_user(user)}, 200)
            return
        if self.path == "/api/admin/login":
            if payload.get("email", "").strip().lower() != ADMIN_EMAIL.lower() or not secrets.compare_digest(str(payload.get("password", "")), ADMIN_PASSWORD):
                self.send_json({"error": "Admin credentials are incorrect."}, 401)
                return
            self.set_session(ADMIN_EMAIL, "admin")
            self.send_json({"admin": {"email": ADMIN_EMAIL}}, 200)
            return
        if self.path == "/api/logout":
            self.clear_session()
            self.send_json({"message": "Logged out."}, 200)
            return
        if self.path == "/api/profile":
            if not session or session["role"] != "user":
                self.send_json({"error": "Please log in first."}, 401)
                return
            try:
                user = update_user(session["id"], payload)
            except RuntimeError as error:
                self.send_json({"error": str(error)}, 400)
                return
            self.send_json({"user": public_user(user)}, 200)
            return
        if self.path == "/api/orders":
            if not session or session["role"] != "user":
                self.send_json({"error": "Log in to place an order."}, 401)
                return
            try:
                create_order(session["id"], payload)
            except RuntimeError as error:
                self.send_json({"error": str(error)}, 400)
                return
            self.send_json({"message": "Your order request has been received."}, 201)
            return
        if self.path == "/api/admin/products":
            if not is_admin(session):
                self.send_json({"error": "Admin login required."}, 401)
                return
            try:
                product = save_product(payload)
            except RuntimeError as error:
                self.send_json({"error": str(error)}, 400)
                return
            self.send_json({"product": product}, 201)
            return
        if self.path == "/api/signup":
            email = str(payload.get("email", "")).strip()
            if not email or "@" not in email:
                self.send_json({"error": "Please enter a valid email address."}, 400)
                return
            lead = {"email": email, "created_at": timestamp(), "user_id": session["id"] if session and session["role"] == "user" else None}
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
            lead["user_id"] = session["id"] if session and session["role"] == "user" else None

        try:
            save_lead(lead)
        except RuntimeError as error:
            self.send_json({"error": str(error)}, 503)
            return
        self.send_json({"message": "Thanks. The IronX team will be in touch soon."}, 201)

    def do_GET(self):
        if self.path == "/api/me":
            session = get_session(self)
            if not session:
                self.send_json({"user": None}, 200)
                return
            if session["role"] == "admin":
                self.send_json({"admin": {"email": ADMIN_EMAIL}}, 200)
                return
            user = get_user(session["id"])
            self.send_json({"user": public_user(user), "orders": get_orders(session["id"])}, 200)
            return
        if self.path == "/api/products":
            self.send_json({"products": get_products(available_only=True)}, 200)
            return
        if self.path == "/api/admin/leads":
            if not is_admin(get_session(self)):
                self.send_json({"error": "Admin login required."}, 401)
                return
            self.send_json({"leads": get_leads()}, 200)
            return
        if self.path == "/api/admin/overview":
            if not is_admin(get_session(self)):
                self.send_json({"error": "Admin login required."}, 401)
                return
            self.send_json({"stats": get_admin_stats(), "users": get_users(), "orders": get_all_orders(), "products": get_products(), "leads": get_leads()}, 200)
            return
        if self.path == "/api/admin/users":
            if not is_admin(get_session(self)):
                self.send_json({"error": "Admin login required."}, 401)
                return
            self.send_json({"users": get_users()}, 200)
            return
        if self.path == "/api/admin/orders":
            if not is_admin(get_session(self)):
                self.send_json({"error": "Admin login required."}, 401)
                return
            self.send_json({"orders": get_all_orders()}, 200)
            return
        super().do_GET()

    def set_session(self, identifier, role):
        token = secrets.token_urlsafe(32)
        SESSIONS[token] = {"id": identifier, "role": role}
        self.send_header_value = ("Set-Cookie", f"ironx_session={token}; Path=/; HttpOnly; SameSite=Lax")

    def clear_session(self):
        token = parse_cookie(self.headers.get("Cookie", ""))
        SESSIONS.pop(token, None)
        self.send_header_value = ("Set-Cookie", "ironx_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")

    def send_json(self, payload, status):
        body = json.dumps(payload, default=json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if hasattr(self, "send_header_value"):
            self.send_header(*self.send_header_value)
            del self.send_header_value
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
    body = json.dumps(payload, default=json_default).encode("utf-8")
    start_response(f"{status} {'Created' if status == 201 else 'Bad Request' if status == 400 else 'Service Unavailable'}", [("Content-Type", "application/json"), ("Content-Length", str(len(body))), ("Cache-Control", "no-store")])
    return [body]


def wsgi_text(start_response, body, status):
    encoded_body = body.encode("utf-8")
    reason = "Not Found" if status == 404 else "Method Not Allowed"
    start_response(f"{status} {reason}", [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(encoded_body)))])
    return [encoded_body]


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def save_lead(lead):
    if not MYSQL_CONFIG["password"]:
        raise RuntimeError("MySQL is not configured. Set MYSQL_PASSWORD before starting the server.")

    try:
        with mysql.connector.connect(**MYSQL_CONFIG) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    insert into leads
                    (user_id, name, age, location, email, phone, height, weight, body_type, preferred_date, preferred_time, created_at)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        lead.get("user_id"), lead.get("name"),
                        int(lead["age"]) if lead.get("age") else None,
                        lead.get("location"),
                        lead["email"],
                        lead.get("phone"),
                        lead.get("height"),
                        lead.get("weight"),
                        lead.get("body_type"), lead.get("preferred_date") or None, lead.get("preferred_time") or None,
                        lead["created_at"],
                    ),
                )
            connection.commit()
    except (mysql.connector.Error, ValueError) as error:
        raise RuntimeError("MySQL could not save the booking. Check the server, password, and schema.") from error


def db_query(query, values=(), fetchone=False, fetchall=False, commit=False):
    if not MYSQL_CONFIG["password"]:
        raise RuntimeError("MySQL is not configured. Set MYSQL_PASSWORD before starting the server.")
    try:
        with mysql.connector.connect(**MYSQL_CONFIG) as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(query, values)
                result = cursor.fetchone() if fetchone else cursor.fetchall() if fetchall else None
            if commit:
                connection.commit()
            return result
    except mysql.connector.Error as error:
        raise RuntimeError("MySQL could not complete the request. Check the server and schema.") from error


def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120000)
    return salt.hex() + ":" + digest.hex()


def password_matches(password, stored):
    try:
        salt, digest = stored.split(":")
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120000).hex()
        return secrets.compare_digest(candidate, digest)
    except (ValueError, AttributeError):
        return False


def register_user(payload):
    name, email, password = str(payload.get("name", "")).strip(), str(payload.get("email", "")).strip().lower(), str(payload.get("password", ""))
    if not name or "@" not in email or len(password) < 8:
        raise RuntimeError("Enter a name, valid email, and password of at least 8 characters.")
    if db_query("select id from users where email = %s", (email,), fetchone=True):
        raise RuntimeError("An account with that email already exists.")
    user_id = db_query("insert into users (name, email, password_hash, phone) values (%s, %s, %s, %s)", (name, email, password_hash(password), str(payload.get("phone", "")).strip()), commit=True)
    return get_user_by_email(email)


def authenticate_user(payload):
    user = get_user_by_email(str(payload.get("email", "")).strip().lower())
    return user if user and password_matches(str(payload.get("password", "")), user["password_hash"]) else None


def get_user(user_id):
    return db_query("select id, name, email, phone, created_at from users where id = %s", (user_id,), fetchone=True)


def get_user_by_email(email):
    return db_query("select id, name, email, phone, password_hash, created_at from users where email = %s", (email,), fetchone=True)


def update_user(user_id, payload):
    name, email, phone = str(payload.get("name", "")).strip(), str(payload.get("email", "")).strip().lower(), str(payload.get("phone", "")).strip()
    if not name or "@" not in email:
        raise RuntimeError("Enter a valid name and email address.")
    db_query("update users set name = %s, email = %s, phone = %s where id = %s", (name, email, phone, user_id), commit=True)
    return get_user(user_id)


def create_order(user_id, payload):
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        product = str(payload.get("product", "")).strip()
        items = [{"product": product, "category": payload.get("category", "store"), "quantity": 1}]
    order_ref = str(uuid.uuid4())
    for item in items:
        product = str(item.get("product", "")).strip()
        quantity = int(item.get("quantity", 1))
        if not product or quantity < 1:
            raise RuntimeError("Choose valid products and quantities.")
        db_query("insert into orders (order_ref, user_id, product_name, category, quantity, total_amount) values (%s, %s, %s, %s, %s, %s)", (order_ref, user_id, product, str(item.get("category", "store")), quantity, float(item.get("price", 0)) * quantity), commit=True)


def get_orders(user_id):
    return db_query("select order_ref, product_name, category, quantity, total_amount, status, created_at from orders where user_id = %s order by created_at desc", (user_id,), fetchall=True)


def get_leads():
    return db_query("select leads.id, leads.name, leads.email, leads.phone, leads.location, leads.body_type, leads.preferred_date, leads.preferred_time, leads.created_at, users.email as account_email from leads left join users on users.id = leads.user_id order by leads.created_at desc", fetchall=True)


def is_admin(session):
    return bool(session and session["role"] == "admin")


def get_users():
    return db_query("select id, name, email, phone, created_at from users order by created_at desc", fetchall=True)


def get_all_orders():
    return db_query("select orders.order_ref, orders.product_name, orders.category, orders.quantity, orders.total_amount, orders.status, orders.created_at, users.name as user_name, users.email as user_email, users.phone as user_phone from orders join users on users.id = orders.user_id order by orders.created_at desc", fetchall=True)


def get_admin_stats():
    counts = db_query("select (select count(*) from users) as users, (select count(*) from orders) as orders, (select count(*) from leads) as bookings, (select count(*) from products) as products", fetchone=True)
    return counts


def get_products(available_only=False):
    query = "select id, name, category, description, price, image_url, available, created_at from products"
    if available_only:
        query += " where available = 1"
    return db_query(query + " order by created_at desc", fetchall=True)


def save_product(payload):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise RuntimeError("Product name is required.")
    price = float(payload.get("price", 0))
    if price < 0:
        raise RuntimeError("Product price cannot be negative.")
    product_id = payload.get("id")
    values = (name, str(payload.get("description", "")).strip(), price, str(payload.get("image_url", "")).strip(), 1 if payload.get("available", True) else 0)
    category = str(payload.get("category", "store")).strip().lower()
    if category not in ("store", "nutrition"):
        raise RuntimeError("Choose a valid product category.")
    if product_id:
        db_query("update products set name = %s, category = %s, description = %s, price = %s, image_url = %s, available = %s where id = %s", (name, category) + values[1:] + (int(product_id),), commit=True)
        return db_query("select id, name, category, description, price, image_url, available, created_at from products where id = %s", (int(product_id),), fetchone=True)
    db_query("insert into products (name, category, description, price, image_url, available) values (%s, %s, %s, %s, %s, %s)", (name, category) + values[1:], commit=True)
    return db_query("select id, name, category, description, price, image_url, available, created_at from products where name = %s order by id desc limit 1", (name,), fetchone=True)


def public_user(user):
    return {key: user[key] for key in ("id", "name", "email", "phone", "created_at") if key in user}


def parse_cookie(cookie_header):
    for item in cookie_header.split(";"):
        key, _, value = item.strip().partition("=")
        if key == "ironx_session":
            return value
    return ""


def get_session(handler):
    return SESSIONS.get(parse_cookie(handler.headers.get("Cookie", "")))


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 5500), IronXRequestHandler)
    print("IronX Gym running at http://127.0.0.1:5500")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping IronX Gym server")
    finally:
        server.server_close()
