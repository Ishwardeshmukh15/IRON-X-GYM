# IronX Gym

A bold, responsive IronX Gym homepage built with plain HTML, CSS, and vanilla JavaScript.

## Run locally

Create the `ironx_gym` database and `leads` table by running [mysql_schema.sql](mysql_schema.sql) in MySQL Workbench. The Python backend connects directly to MySQL with `mysql-connector-python`:

```powershell
python app.py
```

Then visit `http://127.0.0.1:5500`.

Bookings are saved directly in MySQL in the `ironx_gym.leads` table. The password is stored only in the ignored local `.env` file.

## Accounts and admin portal

Run the updated [mysql_schema.sql](mysql_schema.sql) before using accounts. Members can create an account at `/auth.html`, edit their profile at `/dashboard.html`, and request products from the store or nutrition pages. A logged-in member's free-session booking is linked to their account and appears in the admin portal at `/admin.html`.

The portal has one admin identity, configured in `.env`:

```env
MYSQL_PASSWORD=your_mysql_password
IRONX_ADMIN_EMAIL=admin@ironxgym.com
IRONX_ADMIN_PASSWORD=use-a-long-password
```

There is no public admin registration. Product buttons remain usable as a local bag for guests; logged-in members also save their order request to the `orders` table.

The homepage uses Unsplash-hosted training photography and Google Fonts, so an internet connection improves the visual result.
