from rest_framework import serializers
from .models import Listing, Booking, Payment


class ListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = '__all__'


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id", "booking", "tx_ref", "ref_id", "amount", "currency",
            "status", "checkout_url", "init_response", "verify_response",
            "created_at", "updated_at"
        ]
        read_only_fields = ["tx_ref", "ref_id", "status", "checkout_url", "init_response", "verify_response", "created_at", "updated_at"]
