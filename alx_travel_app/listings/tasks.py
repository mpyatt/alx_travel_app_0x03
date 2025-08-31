from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Payment


@shared_task
def send_payment_confirmation_email(payment_id: int):
    payment = Payment.objects.select_related(
        "booking", "booking__listing").get(id=payment_id)
    booking = payment.booking

    subject = f"Booking #{booking.id} payment received"
    message = (
        f"Hello {booking.first_name or ''} {booking.last_name or ''},\n\n"
        f"We have received your payment of {payment.amount} {payment.currency} "
        f"for Booking #{booking.id} ({booking.listing}).\n\n"
        f"Transaction ref: {payment.tx_ref}\n"
        f"Status: {payment.status}\n\nThank you!"
    ).strip()

    recipient = booking.email
    if not recipient and hasattr(booking, "user") and getattr(booking.user, "email", None):
        recipient = booking.user.email

    if not recipient:
        return

    send_mail(
        subject,
        message,
        getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com"),
        [recipient],
        fail_silently=True,
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_booking_confirmation_email(self, booking_id):
    """
    Sends a booking confirmation email asynchronously.

    We try common patterns for the recipient:
    - booking.user.email (if a FK to User exists)
    - booking.email (if the model stores an email directly)
    """
    try:
        from .models import Booking  # local import to avoid early app loading issues
        booking = Booking.objects.get(id=booking_id)
    except Exception as exc:
        # If it doesn't exist or db not ready, just return a message (or retry if needed)
        return f"Booking {booking_id} not sent: {exc}"

    recipient = getattr(getattr(booking, "user", None),
                        "email", None) or getattr(booking, "email", None)
    if not recipient:
        return f"Booking {booking_id} has no recipient email."

    subject = "Booking Confirmation"
    message_lines = [
        "Hello,",
        "",
        f"Your booking #{booking.id} has been received.",
        f"Listing: {getattr(booking, 'listing', None)}",
        f"Check-in: {getattr(booking, 'check_in', None)}",
        f"Check-out: {getattr(booking, 'check_out', None)}",
        "",
        "Thanks for choosing ALX Travel!",
    ]
    message = "\n".join(map(str, message_lines))

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=False,
    )

    return f"Sent confirmation to {recipient}"
