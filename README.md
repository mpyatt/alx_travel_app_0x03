# 🧭 alx_travel_app_0x02

A Django-based API for managing travel listings, bookings, and payments, built with Django REST Framework and integrated with **Chapa** for secure payment processing.

## 📦 Project Structure

* `listings/` — App containing Listings, Bookings, and Payments models, views, serializers, Celery tasks.
* `alx_travel_app/` — Main Django project configuration.
* `db.sqlite3` — SQLite database for local development.
* `requirements.txt` — Python dependencies.

## 🚀 Features

* CRUD operations for travel listings and bookings.
* RESTful API endpoints.
* **Chapa Payment Integration**

  * Initiate payments
  * Verify payments
  * Track status in a `Payment` model
  * Confirmation email via Celery after successful payment
* Swagger UI documentation at `/swagger/`.
* SQLite for development (can be switched to MySQL).
* CORS and environment variable support.

## 📂 Endpoints

| Method | Endpoint                  | Description                          |
| ------ | ------------------------- | ------------------------------------ |
| GET    | `/api/listings/`          | List all listings                    |
| POST   | `/api/listings/`          | Create a new listing                 |
| GET    | `/api/bookings/`          | List all bookings                    |
| POST   | `/api/bookings/`          | Create a new booking                 |
| POST   | `/api/payments/initiate/` | Initiate a Chapa payment for booking |
| GET    | `/api/payments/verify/`   | Verify payment status with Chapa     |
| POST   | `/api/payments/callback/` | (Optional) Webhook callback handler  |

👉 More endpoints and schemas available via Swagger UI.

## 📄 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/mpyatt/alx_travel_app_0x02.git
cd alx_travel_app_0x02/alx_travel_app
```

### 2. Create & Activate a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
CHAPA_SECRET_KEY=CHASECK_TEST-xxxxxxxxxxxxxxx
CHAPA_BASE_URL=https://api.chapa.co
DEFAULT_FROM_EMAIL=no-reply@example.com
```

### 5. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Run the Development Server

```bash
python manage.py runserver
```

Visit [http://127.0.0.1:8000/swagger/](http://127.0.0.1:8000/swagger/) for Swagger documentation.

---

## 🛠 Tech Stack

* Python 3.11+
* Django 4.2
* Django REST Framework
* drf-yasg (Swagger)
* SQLite (default) or MySQL (optional)
* Celery + RabbitMQ/Redis (for async tasks like email)
* Chapa API integration

---

## 💳 Payment Flow

1. User creates a booking.
2. Call `POST /api/payments/initiate/` with booking details → returns `checkout_url`.
3. Redirect user to Chapa checkout.
4. After payment:

   * User is redirected to your `return_url`.
   * Chapa can also hit your `callback_url`.
   * Always confirm via `GET /api/payments/verify/?tx_ref=...`.
5. On success → `Payment.status` becomes `completed` and a confirmation email is sent via Celery.

### Example cURL

#### Initiate

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

#### Verify

```bash
curl "http://127.0.0.1:8000/api/payments/verify/?tx_ref=booking-1-XXXX"
```
