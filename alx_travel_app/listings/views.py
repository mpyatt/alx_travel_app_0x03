from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Listing, Booking, Payment
from .serializers import ListingSerializer, BookingSerializer, PaymentSerializer
from .tasks import send_payment_confirmation_email

import os
import uuid
import requests
from decimal import Decimal
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import transaction

# ---- Regular CRUD ViewSets ----

class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    permission_classes = [permissions.AllowAny]


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.AllowAny]


# ---- Chapa Integration ----

CHAPA_BASE_URL = getattr(settings, "CHAPA_BASE_URL", "https://api.chapa.co")
CHAPA_SECRET_KEY = getattr(settings, "CHAPA_SECRET_KEY", os.environ.get("CHAPA_SECRET_KEY"))


def _auth_headers():
    if not CHAPA_SECRET_KEY:
        raise RuntimeError("CHAPA_SECRET_KEY is not configured.")
    return {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
        "Content-Type": "application/json",
    }


class InitiatePaymentView(APIView):
    """
    POST /api/payments/initiate/
    Body:
      {
        "booking_id": 123,
        "amount": "150.00",             # optional if Booking.price/listing.price available
        "currency": "ETB",              # optional (default ETB)
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": "0912345678",   # optional
        "return_url": "https://app/paid",
        "callback_url": "https://api/payments/callback/"
      }
    Response: { "checkout_url": "..." , "tx_ref": "..." }
    """
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        data = request.data
        booking = get_object_or_404(Booking, pk=data.get("booking_id"))

        # Amount resolution: body -> booking.price -> listing.price
        body_amount = data.get("amount")
        if body_amount is not None:
            amount = Decimal(str(body_amount))
        elif booking.price is not None:
            amount = Decimal(str(booking.price))
        elif hasattr(booking, "listing") and booking.listing and booking.listing.price:
            amount = Decimal(str(booking.listing.price))
        else:
            return Response({"detail": "amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"detail": "amount must be > 0"}, status=status.HTTP_400_BAD_REQUEST)

        currency = data.get("currency", "ETB")
        email = data.get("email") or booking.email
        first_name = data.get("first_name") or booking.first_name
        last_name = data.get("last_name") or booking.last_name

        missing = [k for k, v in {"email": email, "first_name": first_name, "last_name": last_name}.items() if not v]
        if missing:
            return Response({"detail": f"Missing fields: {', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)

        existing = Payment.objects.filter(
            booking=booking, amount=amount, status=Payment.Status.PENDING
        ).order_by("-created_at").first()
        if existing and existing.checkout_url:
            return Response({"checkout_url": existing.checkout_url, "tx_ref": existing.tx_ref}, status=status.HTTP_200_OK)

        # Generate tx_ref
        tx_ref = f"booking-{booking.id}-{uuid.uuid4().hex[:10]}"

        payment = Payment.objects.create(
            booking=booking,
            tx_ref=tx_ref,
            amount=amount,
            currency=currency,
            status=Payment.Status.PENDING,
        )

        payload = {
            "amount": str(amount),
            "currency": currency,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "tx_ref": tx_ref,
            "callback_url": data.get("callback_url"),
            "return_url": data.get("return_url"),
            "customization": {
                "title": f"Booking #{booking.id}",
                "description": "Booking payment",
            },
        }

        try:
            resp = requests.post(
                f"{CHAPA_BASE_URL}/v1/transaction/initialize",
                json=payload,
                headers=_auth_headers(),
                timeout=20,
            )
            resp.raise_for_status()
            init_json = resp.json()
        except requests.RequestException as e:
            payment.status = Payment.Status.FAILED
            payment.init_response = {"error": str(e)}
            payment.save(update_fields=["status", "init_response", "updated_at"])
            return Response({"detail": "Failed to initiate payment."}, status=status.HTTP_502_BAD_GATEWAY)

        # Chapa may return 200 but error payload
        if str(init_json.get("status")).lower() not in ("success",):
            payment.status = Payment.Status.FAILED
            payment.init_response = init_json
            payment.save(update_fields=["status", "init_response", "updated_at"])
            return Response({"detail": "Payment initialization failed.", "chapa": init_json}, status=status.HTTP_502_BAD_GATEWAY)

        payment.init_response = init_json
        checkout_url = (init_json.get("data") or {}).get("checkout_url")

        if not checkout_url:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "init_response", "updated_at"])
            return Response({"detail": "Chapa did not return a checkout_url."}, status=status.HTTP_502_BAD_GATEWAY)

        payment.checkout_url = checkout_url
        payment.save(update_fields=["checkout_url", "init_response", "updated_at"])

        return Response({"checkout_url": checkout_url, "tx_ref": tx_ref}, status=status.HTTP_201_CREATED)


class VerifyPaymentView(APIView):
    """
    GET /api/payments/verify/?tx_ref=...
    Response: { "status": "completed|failed|pending", "payment_id": ..., "verify": {...} }
    """
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def get(self, request):
        tx_ref = request.query_params.get("tx_ref")
        if not tx_ref:
            return Response({"detail": "tx_ref is required."}, status=status.HTTP_400_BAD_REQUEST)

        payment = get_object_or_404(Payment, tx_ref=tx_ref)

        try:
            resp = requests.get(
                f"{CHAPA_BASE_URL}/v1/transaction/verify/{tx_ref}",
                headers=_auth_headers(),
                timeout=20,
            )
            resp.raise_for_status()
            vjson = resp.json()
        except requests.RequestException as e:
            return Response({"detail": f"Verify request failed: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        payment.verify_response = vjson

        data = vjson.get("data") or {}
        nested_status = (data.get("status") or "").lower()
        top_status = (vjson.get("status") or "").lower()

        if nested_status == "success" or top_status == "success":
            new_status = Payment.Status.COMPLETED
        elif nested_status == "failed" or top_status == "failed":
            new_status = Payment.Status.FAILED
        else:
            new_status = Payment.Status.PENDING

        payment.ref_id = data.get("reference") or data.get("ref_id") or payment.ref_id
        payment.status = new_status
        payment.save(update_fields=["status", "ref_id", "verify_response", "updated_at"])

        if new_status == Payment.Status.COMPLETED:
            try:
                send_payment_confirmation_email.delay(payment.id)
            except Exception:
                # Don't fail response if queue is down
                pass

        return Response(
            {
                "payment_id": payment.id,
                "tx_ref": payment.tx_ref,
                "status": payment.status,
                "ref_id": payment.ref_id,
                "verify": vjson,
            },
            status=status.HTTP_200_OK,
        )


class ChapaCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        tx_ref = request.data.get("tx_ref")
        if not tx_ref:
            return Response({"detail": "tx_ref missing"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_202_ACCEPTED)
