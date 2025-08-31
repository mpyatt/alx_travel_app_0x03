# 🧭 alx_travel_app_0x03

A Django + Django REST Framework API for travel listings, bookings, and payments, with:

- **Celery** background tasks (RabbitMQ/Redis) for email notifications
- **Chapa** payment integration (initiate + verify)  
- **Swagger** API docs

---

## 📦 Project Structure

```sh

alx_travel_app_0x03/
├── alx_travel_app/          # Main Django project (settings, celery config)
├── listings/                # App: models, serializers, viewsets, tasks
├── requirements.txt
├── db.sqlite3               # Local dev DB (optional)
└── README.md

````

- `listings/tasks.py` — Celery tasks (e.g., booking confirmation email)
- `alx_travel_app/celery.py` — Celery app/bootstrap
- `alx_travel_app/settings.py` — Celery + email + Chapa config

---

## 🚀 Features

- CRUD for **Listings** and **Bookings**
- **Chapa** Payments:
  - Initiate payment
  - Verify payment
  - Track status in `Payment` model
  - **Send confirmation email via Celery** on success
- **Email on Booking Creation** (async via Celery)
- Swagger UI at `/swagger/`
- SQLite for dev; switchable to MySQL/PostgreSQL
- CORS + `.env` environment variables

---

## 📂 API Endpoints

| Method | Endpoint                  | Description                                     |
|-------:|---------------------------|-------------------------------------------------|
| GET    | `/api/listings/`          | List all listings                               |
| POST   | `/api/listings/`          | Create a listing                                |
| GET    | `/api/bookings/`          | List all bookings                               |
| POST   | `/api/bookings/`          | Create a booking *(triggers email via Celery)*  |
| POST   | `/api/payments/initiate/` | Initiate a Chapa payment for a booking          |
| GET    | `/api/payments/verify/`   | Verify payment status with Chapa                |
| POST   | `/api/payments/callback/` | (Optional) Webhook callback handler             |

👉 Explore full schemas in **Swagger** at `/swagger/`.

---

## 🛠 Tech Stack

- Python 3.11+
- Django 4.2 + DRF
- Celery 5.x + RabbitMQ (or Redis)
- drf-yasg (Swagger)
- SQLite (dev) / MySQL / Postgres
- Chapa API

---

## ⚙️ Setup

### 1) Clone & enter the project

```bash
git clone git@github.com:attaradev/alx_travel_app_0x03.git
cd alx_travel_app_0x03
````

> If you see auth errors, confirm your remote is under **attaradev** and you have access.

### 2) Create & activate a virtualenv

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Environment variables

Create a `.env` in the project root:

```env
# --- Chapa ---
CHAPA_SECRET_KEY=CHASECK_TEST-xxxxxxxxxxxxxxxx
CHAPA_BASE_URL=https://api.chapa.co

# --- Email (dev defaults to console backend) ---
DEFAULT_FROM_EMAIL=no-reply@example.com
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
# For SMTP in prod (example):
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.your-domain.com
# EMAIL_HOST_USER=apikey
# EMAIL_HOST_PASSWORD=secret
# EMAIL_PORT=587
# EMAIL_USE_TLS=1

# --- Celery ---
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=rpc://
# Or Redis alternative:
# CELERY_BROKER_URL=redis://localhost:6379/0
# CELERY_RESULT_BACKEND=redis://localhost:6379/1

# --- Django ---
DEBUG=1
ALLOWED_HOSTS=127.0.0.1,localhost
```

> Dev uses the **console email backend**, so emails print in the Django console.

### 5) Start a broker

**RabbitMQ via Docker (recommended for dev):**

```bash
docker run -d --hostname rabbit --name rabbit \
  -p 5672:5672 -p 15672:15672 rabbitmq:3-management
# Management UI: http://localhost:15672  (user: guest / pass: guest)
```

*(Or run Redis if you prefer.)*

### 6) Migrations

```bash
python manage.py migrate
```

### 7) Run the app + worker

**Celery worker** (Terminal #1):

```bash
celery -A alx_travel_app worker -l info
```

**Django server** (Terminal #2):

```bash
python manage.py runserver
```

**Swagger**: [http://127.0.0.1:8000/swagger/](http://127.0.0.1:8000/swagger/)

---

## ✉️ Background Emails

- **On booking creation** → `send_booking_confirmation_email` runs in Celery to send a confirmation.
- **On successful payment** (after verify) → a payment confirmation email is sent via Celery.

---

## 💳 Payment Flow (Chapa)

1. Create a booking.
2. `POST /api/payments/initiate/` → returns `checkout_url`.
3. Redirect the user to Chapa checkout.
4. After payment:

   - User redirected to `return_url`.
   - (Optional) Chapa calls your `callback_url`.
   - Always **verify** with `GET /api/payments/verify/?tx_ref=...`.
5. On success:

   - `Payment.status` → `completed`
   - Celery sends a **confirmation email**.

### Example: Initiate

```bash
curl -X POST http://127.0.0.1:8000/api/payments/initiate/ \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": 1,
    "amount": "150.00",
    "currency": "ETB",
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "return_url": "http://localhost:8000/thanks",
    "callback_url": "http://localhost:8000/api/payments/callback/"
  }'
```

### Example: Verify

```bash
curl "http://127.0.0.1:8000/api/payments/verify/?tx_ref=booking-1-XXXX"
```

---

## 🧪 Quick Test: Booking Email (Celery)

Create a booking (adjust fields to your serializer):

```bash
curl -X POST http://127.0.0.1:8000/api/bookings/ \
  -H "Content-Type: application/json" \
  -d '{
    "listing": 1,
    "check_in": "2025-09-10",
    "check_out": "2025-09-12",
    "email": "test@example.com"
  }'
```

- Watch **Celery worker** logs (Terminal #1) for task pickup.
- With the console backend, the **email content prints** in the Django server logs.

---

## 🧰 Troubleshooting

- **Repo not found on push**: ensure remote is `git@github.com:attaradev/alx_travel_app_0x03.git` and the repo exists under **attaradev**.
- **No Celery tasks running**: verify the worker is running and `CELERY_BROKER_URL` matches your broker.
- **Emails not sent**:

  - In dev, check the Django console output.
  - In prod, configure SMTP env vars and check credentials/ports.
