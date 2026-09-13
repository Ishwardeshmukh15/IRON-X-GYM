# IronX Gym

A bold, responsive IronX Gym homepage built with plain HTML, CSS, and vanilla JavaScript.

## Run locally

Create the `ironx_gym` database and `leads` table by running [mysql_schema.sql](mysql_schema.sql) in MySQL Workbench. The Python backend connects directly to MySQL with `mysql-connector-python`:

```powershell
python app.py
```

Then visit `http://127.0.0.1:5500`.

Bookings are saved directly in MySQL in the `ironx_gym.leads` table. The password is stored only in the ignored local `.env` file.

The homepage uses Unsplash-hosted training photography and Google Fonts, so an internet connection improves the visual result.
