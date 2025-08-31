from django.db import models
from django.utils import timezone
from decimal import Decimal


class Listing(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Booking(models.Model):
    listing = models.ForeignKey(
        Listing, related_name='bookings', on_delete=models.CASCADE)
    guest_name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking by {self.guest_name} for {self.listing}"

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    booking = models.ForeignKey("listings.Booking", on_delete=models.CASCADE, related_name="payments")

    # Chapa references
    tx_ref = models.CharField(max_length=128, unique=True, db_index=True)
    ref_id = models.CharField(max_length=128, blank=True, null=True)

    # Money
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="ETB")

    # Status & links
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    checkout_url = models.URLField(blank=True, null=True)

    # Raw API payloads (handy for debugging/audits)
    init_response = models.JSONField(blank=True, null=True)
    verify_response = models.JSONField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment(tx_ref={self.tx_ref}, status={self.status}, amount={self.amount} {self.currency})"
