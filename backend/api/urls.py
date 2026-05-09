from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    RegisterView,
    LoginView,
    ForgotPasswordView,
    ResetPasswordView,
    CurrentUserView,
    LogoutView,
    UserAccountUpdateView,
    CreateReportView,
    FAQListView,
    ContactCreateView,
    TherapistViewSet,
    FavoriteViewSet,
    BookingViewSet,
    TherapistAppointmentViewSet,
    PatientSessionViewSet,
    MedicineViewSet,
    SpecializationViewSet,
    OnboardingSurveyViewSet,
    NeureaChatView,
    MoodDashboardView,
    UserHomeViewSet,
    NotificationViewSet,
    SupportMetadataView,
    ExploreCategoryViewSet,
)

router = DefaultRouter()

router.register(r'therapists', TherapistViewSet, basename='therapist')
router.register(r'favorites', FavoriteViewSet, basename='favorite')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'appointments', TherapistAppointmentViewSet, basename='appointment')
router.register(r'sessions', PatientSessionViewSet, basename='session')
router.register(r'medicines', MedicineViewSet, basename='medicine')
router.register(r'specializations', SpecializationViewSet, basename='specialization')
router.register(r'onboarding-survey', OnboardingSurveyViewSet, basename='onboarding-survey')
router.register(r'home', UserHomeViewSet, basename='user-home')
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'explore', ExploreCategoryViewSet, basename='explore')
urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/update/', UserAccountUpdateView.as_view(), name='update-profile'),
    path('reports/create/', CreateReportView.as_view(), name='create-report'),
    path('help/faq/', FAQListView.as_view(), name='faq-list'),
    path('help/contact/', ContactCreateView.as_view(), name='contact-create'),
    path('', include(router.urls)),
    path('chatbot/', NeureaChatView.as_view(), name='neurea-chat'),
    path('mood-dashboard/', MoodDashboardView.as_view(), name='mood-dashboard'),
    path('account/support-options/', SupportMetadataView.as_view(), name='support-options'),
    
]