from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ListingViewSet,
    BookingViewSet,
    InitiatePaymentView,
    VerifyPaymentView,
    ChapaCallbackView,
)

router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),

    # Payments
    path('payments/initiate/', InitiatePaymentView.as_view(), name='payments-initiate'),
    path('payments/verify/', VerifyPaymentView.as_view(), name='payments-verify'),
    path('payments/callback/', ChapaCallbackView.as_view(), name='payments-callback'),
]
