from django.contrib import admin
from .models import Listing, Booking, Payment

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "price", "created_at")
    search_fields = ("title",)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "price", "email", "created_at")
    search_fields = ("id", "listing__title", "email")

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "tx_ref", "status", "amount", "currency", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("tx_ref", "ref_id", "booking__id")
