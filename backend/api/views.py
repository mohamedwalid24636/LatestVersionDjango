from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware
from django.db import transaction, models
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import generics, permissions
from rest_framework_simplejwt.exceptions import TokenError
from datetime import timedelta
from collections import defaultdict
import datetime
from .serializers import (
    UserRegistrationSerializer,
    LoginSerializer,
    ForgotPasswordRequestSerializer,
    ResetPasswordSerializer,
    TherapistListSerializer,
    TherapistDetailSerializer,
    AvailabilitySlotSerializer,
    BookingConfirmationSerializer,
    ExploreCategorySerializer,
    TherapistDashboardSerializer,
    UserAccountUpdateSerializer,
    ReportSerializer,
    FAQSerializer,
    ContactMessageSerializer,
    MedicineSerializer,
    SessionSerializer,
    UserHomeSerializer,
    MoodLogSerializer,
    FavoriteSerializer,
    PatientSurveySerializer,
    NotificationSerializer,
    ExploreItemSerializer,
    ChangePasswordSerializer,
)
from .models import (
    PasswordResetCode, 
    TherapistProfile, 
    Favorite,PatientTherapist,
    ExploreCategory,
    AvailabilitySlot,
    FAQ,Session,
    Medicine,
    MoodLog,
    Payment,PatientOnboardingSurvey,
    PatientProfile,
    Conversation, 
    Message,
    Alert,
    ReportType,
    ContactCategory,
    AlertTime,
)

User = get_user_model()
class UserHomeViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def get_dashboard(self, request):
    
        serializer = UserHomeSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def submit_mood(self, request):
        mood_type = request.data.get("mood")
        note = request.data.get("note", "")

        if not mood_type:
            return Response({"error": "Mood is required"}, status=status.HTTP_400_BAD_REQUEST)

        mood = MoodLog.objects.create(
            user=request.user,
            mood_type=mood_type,
            note=note
        )

        return Response({
            "message": "Mood logged successfully.",
            "mood_type": mood.mood_type,
            "mood_value": mood.mood_value,
            "created_at": mood.created_at
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def mood_history(self, request):
       
        history = MoodLog.objects.filter(user=request.user).order_by('-created_at')
        serializer = MoodLogSerializer(history, many=True)
        return Response(serializer.data)
class UserAccountUpdateView(generics.UpdateAPIView):
    serializer_class = UserAccountUpdateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user
    
class SupportMetadataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        report_types = ReportType.objects.all().values('id', 'name', 'code')
        contact_cats = ContactCategory.objects.all().values('id', 'name', 'code')
        
        return Response({
            "report_choices": list(report_types),
            "contact_choices": list(contact_cats)
        })
class CreateReportView(generics.CreateAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ContactCreateView(generics.CreateAPIView):
    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class FAQListView(generics.ListAPIView):
    queryset = FAQ.objects.all().order_by('order')
    serializer_class = FAQSerializer
    permission_classes = [permissions.AllowAny] 
from .tasks import send_async_email
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        has_completed_survey = False
        if user.role == 'patient':
            from .models import PatientProfile
            PatientProfile.objects.get_or_create(user=user)
            has_completed_survey = False 
        elif user.role == 'therapist':
            has_completed_survey = True 
        subject = 'Welcome to Neurea'
        message = f"Hello {user.first_name}, welcome to Neurea!"
        send_async_email.delay(subject, message, [user.email])
        try:
            new_alert = Alert.objects.create(
                user=user,
                type='registration',
                message=f"New {user.role} joined: {user.first_name}"
            )
            AlertTime.objects.create(alert=new_alert)
        except: pass

        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role                                                                              # Mohamed Walid Added      
        refresh["email"] = user.email            
        refresh['is_superuser'] = user.is_superuser
                                                                        # Mohamed Walid           
        return Response({'message': 'User registered successfully.'}, status=201)



class OnboardingSurveyViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PatientSurveySerializer 

    def create(self, request):
        if request.user.role != 'patient':
            return Response(
                {"error": "Only patients can complete the onboarding survey."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PatientOnboardingSurvey.objects.update_or_create(
            user=request.user,
            defaults=serializer.validated_data
        )
        profile, created = PatientProfile.objects.get_or_create(user=request.user)
        profile.has_completed_survey = True
        profile.save()

        return Response({
            "status": "success", 
            "message": "Survey completed, welcome to Neurea!",
            "has_completed_survey": True
        }, status=status.HTTP_201_CREATED)
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)


        refresh['role'] = user.role                                     #Added by Mohamed Walid
        refresh["email"] = user.email
        refresh['is_superuser'] = user.is_superuser

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
            }
        })


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        reset_code = PasswordResetCode.generate_code(email)

        subject = 'Password Reset Code - Care App'
        message = f'Your password reset code is: {reset_code.code}\nThis code expires in 15 minutes.'
    
        send_async_email.delay(subject, message, [email])

        return Response({
            'message': 'Verification code sent to your Gmail.'
        }, status=status.HTTP_200_OK)
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reset_code = serializer.validated_data['reset_code']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(email=reset_code.email)
            user.set_password(new_password)
            user.save()

            subject = 'Security Alert: Password Changed'
            message = "Your password has been changed successfully."
            send_async_email.delay(subject, message, [user.email])

            reset_code.delete()
            return Response({'message': 'Password reset successfully.'}, status=200)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=404)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'gender': user.gender,
            'birthday': user.birthday,
            'profile_image': user.profile_image.url if user.profile_image else None,
        })
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)

            token = RefreshToken(refresh_token)
            token.blacklist() 

            return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except TokenError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TherapistViewSet(viewsets.ReadOnlyModelViewSet):
    # queryset = TherapistProfile.objects.select_related('user').all()
    queryset = TherapistProfile.objects.select_related('user').exclude(
        specialization="Admin"
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'specialization': ['icontains', 'exact'],
    }
    
    search_fields = ['user__first_name', 'user__last_name', 'specialization']
    
    ordering_fields = ['avg_rating', 'patients_count']
    ordering = ['-avg_rating']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TherapistDetailSerializer
        return TherapistListSerializer

    def get_serializer_context(self):
        return {'request': self.request}

class FavoriteViewSet(viewsets.GenericViewSet):
    serializer_class = FavoriteSerializer

    @action(detail=True, methods=['post'], url_path='toggle')
    def toggle_favorite(self, request, pk=None):
        therapist = TherapistProfile.objects.get(pk=pk)
        favorite, created = Favorite.objects.get_or_create(user=request.user, therapist=therapist)
        if not created:
            favorite.delete()
            return Response({'is_favorited': False})
        return Response({'is_favorited': True})

    @action(detail=False, methods=['get'], url_path='my_favorites')
    def my_favorites(self, request):
        fav_therapists = TherapistProfile.objects.filter(favorited_by__user=request.user)
        serializer = TherapistListSerializer(fav_therapists, many=True, context={'request': request})
        return Response(serializer.data)

class BookingViewSet(viewsets.GenericViewSet):
    serializer_class = BookingConfirmationSerializer

    @action(detail=True, methods=['get'], url_path='available_slots')
    def available_slots(self, request, pk=None):
        therapist = TherapistProfile.objects.get(pk=pk)
        now = timezone.now()
        current_date = now.date()
        current_time = now.time()
        therapist.availability_slots.filter(
            is_booked=False
        ).filter(
            models.Q(date__lt=current_date) | 
            models.Q(date=current_date, start_time__lt=current_time)
        ).delete()
        slots = therapist.availability_slots.filter(is_booked=False).filter(
            models.Q(date__gt=current_date) |
            models.Q(date=current_date, start_time__gt=current_time)
        ).order_by('date', 'start_time')

        serializer = AvailabilitySlotSerializer(slots, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='confirm')
    @transaction.atomic
    def confirm_booking(self, request, pk=None):
        therapist_profile = TherapistProfile.objects.get(pk=pk)
        serializer = BookingConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        slot_ids = serializer.validated_data['slot_ids']
        
        
        total_amount = therapist_profile.hourly_rate * len(slot_ids)

        slots = therapist_profile.availability_slots.filter(id__in=slot_ids)
        slots.update(is_booked=True, patient=request.user)


        for slot in slots:
            naive_datetime = datetime.datetime.combine(slot.date, slot.start_time)
            aware_datetime = make_aware(naive_datetime)
            Session.objects.create(
                patient=request.user,
                therapist=therapist_profile.user,
                session_date=aware_datetime,
                progress_level='new',
                status='scheduled',
                meeting_link=f"https://meet.google.com/lookup/{therapist_profile.user.username}"
            )


        Payment.objects.create(
            patient=request.user,
            therapist=therapist_profile,
            amount=total_amount,
            transaction_id=f"PAY-{timezone.now().timestamp()}",
            status='completed'
        )
        try:
            new_alert = Alert.objects.create(
                user=request.user,
                type='payment',
                message=(
                    f"Successful Payment: {total_amount} EGP from "
                    f"{request.user.get_full_name()} to Dr. {therapist_profile.user.get_full_name()}"
                )
            )
            AlertTime.objects.create(alert=new_alert)                             #Mohamed Walid

            # تنبيه جديد للدكتور
            therapist_alert = Alert.objects.create(
                user=therapist_profile.user,
                type='appointment',
                message=(
                    f"New session booked by {request.user.get_full_name()}."
                )
            )
            AlertTime.objects.create(alert=therapist_alert)

        except Exception as alert_error:
            print(f"Error creating Payment alerts: {alert_error}")

           
        already_patient = PatientTherapist.objects.filter(
            patient=request.user, therapist=therapist_profile.user
        ).exists()
        new_patient = not already_patient
        if new_patient:
            PatientTherapist.objects.create(patient=request.user, therapist=therapist_profile.user)
            therapist_profile.patients_count += 1
            therapist_profile.save()

        
        image_url = None
        if therapist_profile.user.profile_image:
            image_url = therapist_profile.user.profile_image.url
        else:
            image_url = None

        return Response({
            'status': 'success',
            'message': 'Payment Success !',
            'data': {
                'doctor_name': therapist_profile.user.get_full_name(),
                'doctor_image': image_url,
                'specialization': getattr(therapist_profile, 'specialization', 'Therapist'),
                'total_amount': total_amount,
                'currency': 'EGP',
                'booked_slots': AvailabilitySlotSerializer(slots, many=True, context={'request': request}).data,
                'new_patient': new_patient
            }
        }, status=200)

class TherapistAppointmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TherapistDashboardSerializer

    def get_queryset(self):
        if not hasattr(self.request.user, 'therapist_profile'):
            return AvailabilitySlot.objects.none()
        return AvailabilitySlot.objects.filter(
            therapist=self.request.user.therapist_profile,
            is_booked=True,
            patient__isnull=False
        ).select_related('patient').order_by('date', 'start_time')


class PatientSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SessionSerializer

    def get_queryset(self):
        return Session.objects.filter(patient=self.request.user).select_related(
            'therapist', 'therapist__therapist_profile'
        ).order_by('-session_date')

    @action(detail=True, methods=['post'], url_path='cancel')
    @transaction.atomic
    def cancel_session(self, request, pk=None):
        try:
            session = self.get_queryset().get(session_id=pk)
        except Session.DoesNotExist:
            return Response({'error': 'Session not found or unauthorized.'}, status=404)

        now = timezone.now()
        time_until_session = session.session_date - now

        if time_until_session >= datetime.timedelta(hours=12):
            penalty = 0.10
            refund = 0.90
            msg = "Cancelled more than 12h early. 10% fee applied."
        else:
            penalty = 0.50
            refund = 0.50
            msg = "Cancelled late (less than 12h). 50% fee applied."

        AvailabilitySlot.objects.filter(
            therapist__user=session.therapist,
            date=session.session_date.date(),
            start_time=session.session_date.time(),
            is_booked=True
        ).update(is_booked=False, patient=None)


        payment = Payment.objects.filter(
            patient=request.user, therapist__user=session.therapist
        ).last()
        refund_amount = 0
        if payment:
            refund_amount = float(payment.amount) * refund
            payment.status = 'refunded'
            payment.save()

       
        session.delete()  

        other_sessions = Session.objects.filter(
            patient=request.user,
            therapist=session.therapist,
            status='scheduled'
        ).exclude(session_id=pk)

        if not other_sessions.exists():
            PatientTherapist.objects.filter(
                patient=request.user,
                therapist=session.therapist
            ).delete()

            therapist_profile = session.therapist.therapist_profile
            if therapist_profile.patients_count > 0:
                therapist_profile.patients_count -= 1
                therapist_profile.save()
        try:
            
            new_alert = Alert.objects.create(
                user=request.user,
                type='emergency',
                message=(
                    f"Booking Cancelled: Patient {request.user.get_full_name()} "
                    f"cancelled their session with Dr. {session.therapist.get_full_name()}"
                )
            )
            AlertTime.objects.create(alert=new_alert)
        except Exception as alert_error:
            print(f"Error creating cancellation alert: {alert_error}")

        return Response({
            'status': 'success',
            'message': msg,
            'refund_amount': refund_amount,
            'penalty_applied': f"{penalty * 100}%",
            'patient_therapist_removed': not other_sessions.exists()
        }, status=200)

class MedicineViewSet(viewsets.ModelViewSet):

    serializer_class = MedicineSerializer

    def get_queryset(self):

        user = self.request.user

        # Therapist
        if hasattr(user, 'therapist_profile'):
            return Medicine.objects.filter(prescribed_by=user)

        # Patient
        return Medicine.objects.filter(
            patient=user,
            is_active=True
        )

    def perform_create(self, serializer):

        user = self.request.user

        if not hasattr(user, 'therapist_profile'):
            raise PermissionError("Only therapists can prescribe medicine.")

        patient_id = self.request.data.get("patient_id")

        if not patient_id:
            raise ValueError("patient_id is required")

        serializer.save(
            prescribed_by=user,
            patient_id=patient_id
        )

    @action(detail=True, methods=['post'], url_path='mark_taken')
    def mark_as_taken(self, request, pk=None):

        medicine = self.get_object()

        if medicine.patient != request.user:
            return Response({'error': 'Not your medicine'}, status=403)

        medicine.notes = (medicine.notes or "") + \
            f"\n[Taken on {timezone.now().strftime('%Y-%m-%d %H:%M')}]"

        medicine.save()

        return Response({
            'status': 'success',
            'message': f'{medicine.name} marked as taken.'
        })

class SpecializationViewSet(viewsets.GenericViewSet):
    @action(detail=False, methods=['get'])
    def popular(self, request):
        specs = TherapistProfile.objects.values('specialization') \
            .annotate(total=models.Count('specialization')) \
            .order_by('-total')
        return Response(specs)
    
class TherapistDashboardViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not hasattr(self.request.user, 'therapist_profile'):
            return AvailabilitySlot.objects.none()
        return AvailabilitySlot.objects.filter(
            therapist=self.request.user.therapist_profile,
            is_booked=True,
            patient__isnull=False
        ).select_related('patient').order_by('date', 'start_time')

    @action(detail=False, methods=['get'], url_path='my_appointments')
    def my_appointments(self, request):
        
        if not hasattr(request.user, 'therapist_profile'):
            return Response(
                {'error': 'Access denied. User is not a therapist.'},
                status=status.HTTP_403_FORBIDDEN
            )
        appointments = self.get_queryset()
        serializer = TherapistDashboardSerializer(appointments, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='prescribe_medicine')
    @transaction.atomic
    def prescribe_medicine(self, request):
      
        if not hasattr(request.user, 'therapist_profile'):
            return Response(
                {'error': 'Only therapists can prescribe medicine.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        
        patient_id = request.data.get('patient_id')
        if not patient_id:
            return Response(
                {'patient_id': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = MedicineSerializer(data=request.data)
        if serializer.is_valid():
            
            serializer.save(user_id=patient_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ExploreCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExploreCategory.objects.all()
    serializer_class = ExploreCategorySerializer

    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        category = self.get_object()
        items = category.items.all().only('title', 'external_url', 'image', 'duration')
        serializer = ExploreItemSerializer(items, many=True, context={'request': request})
        return Response(serializer.data)

import threading
from .models import Conversation, Message
from .utils.chatbot import ask_yousef_chatbot
from .utils.sms import trigger_emergency_protocol
from .tasks import send_emergency_whatsapp_task
class NeureaChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user_message_text = request.data.get("message")

        if not user_message_text:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        conversation, created = Conversation.objects.get_or_create(
            patient=user,
            status='active',
            defaults={'start_time': timezone.now()}
        )
        
        user_msg_obj = Message.objects.create(
            conversation=conversation,
            sender=user,
            sender_type='patient',
            message=user_message_text
        )

        ai_data = ask_yousef_chatbot(user_message_text)
        
        if ai_data:
            bot_reply = ai_data['reply']
            emotion = ai_data['emotion']
            crisis_info = ai_data['crisis_info']
        else:
            bot_reply = "I'm having trouble connecting, but I'm here for you."
            emotion, crisis_info = "neutral", "no_data"

        bot_msg_obj = Message.objects.create(
            conversation=conversation,
            sender=None, 
            sender_type='system',
            message=bot_reply
        )
        
        is_crisis = "HIGH" in str(emotion).upper() or "SUICIDE" in user_message_text.lower() or "END MY LIFE" in user_message_text.upper()
        
        if is_crisis:
            send_emergency_whatsapp_task.delay(user.id, f"User said: {user_message_text}")
            
            conversation.avg_risk_level = 1.0
            conversation.recommended_action = "Immediate Clinical Intervention Required"
            conversation.save()

        MoodLog.objects.create(
            user=user,
            mood_type=emotion,
            note=f"Auto-logged from conversation: {emotion}"
        )

        return Response({
            "reply": bot_reply,
            "detected_emotion": emotion,
            "is_crisis": is_crisis,
            "conversation_id": conversation.conversation_id
        }, status=status.HTTP_200_OK)

from rest_framework.decorators import api_view, permission_classes
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_mood(request):
    user = request.user
    today = timezone.now().date()
    
    mood_type = request.data.get("mood_type")
    note = request.data.get("note", "")

    if not mood_type:
        return Response({"error": "mood_type is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Use filter instead of get to safely handle duplicate entries
    existing_logs = MoodLog.objects.filter(
        user=user, 
        created_at__date=today
    )

    if existing_logs.exists():
        # Update the first matching log safely
        mood = existing_logs.first()
        mood.mood_type = mood_type
        mood.note = note
        mood.save()
        created = False
    else:
        # Create a brand new log if none exist for today
        mood = MoodLog.objects.create(
            user=user,
            mood_type=mood_type,
            note=note
        )
        created = True

    return Response({
        "message": "Mood submitted successfully",
        "created": created,
        "mood_value": mood.mood_value
    }, status=status.HTTP_200_OK)



class MoodDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]

        # Read-only fetch of last 7 days of logs
        mood_logs = MoodLog.objects.filter(
            user=user,
            created_at__date__gte=last_7_days[0]
        )

        grouped = defaultdict(list)
        for m in mood_logs:
            grouped[m.created_at.date()].append(m.mood_value)

        mood_trend = []
        total_points = 0
        count = 0

        for day in last_7_days:
            day_moods = grouped.get(day, [])

            if day_moods:
                avg = sum(day_moods) / len(day_moods)
            else:
                avg = 0

            mood_trend.append({
                "day": day.strftime('%a'),
                "value": round(avg * 20, 1)  
            })

            if avg > 0:
                total_points += avg
                count += 1

        actual_avg = (total_points / count) if count > 0 else 0
        display_avg = round(actual_avg * 2, 1)

        sessions_count = Session.objects.filter(
            patient=user,
            session_date__date__gte=last_7_days[0]
        ).count()

        msg_count = Message.objects.filter(
            sender=user,
            timestamp__date__gte=last_7_days[0]
        ).count()

        minutes_spent = int((sessions_count * 50) + (msg_count * 1.5))

        goals = {
            "meditation": 80,
            "chat": min(msg_count * 10, 100),
            "checkin": min(count * 15, 100),
            "breathing": 40,
            "therapy": min(sessions_count * 25, 100)
        }

        return Response({
            "mood_trend": mood_trend,
            "avg_mood": display_avg,
            "sessions": sessions_count,
            "minutes": minutes_spent,
            "goals": goals,
            "insight": self.get_ai_insight(actual_avg)
        })

    def get_ai_insight(self, avg):
        if avg >= 4:
            return "You show improved mood this week. Keep your habits consistent!"
        elif avg <= 2.5:
            return "Your mood has been low. Consider talking to a therapist or using relaxation exercises."
        else:
            return "You're maintaining a balanced mood. Keep tracking daily."
class NotificationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Alert.objects.filter(user=user).order_by('-created_at')
        
        status_param = self.request.query_params.get('status')
        if status_param == 'unread':
            return queryset.filter(resolved_at__isnull=True)
        elif status_param == 'read':
            return queryset.filter(resolved_at__isnull=False)
            
        return queryset

   
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        from django.utils import timezone
        Alert.objects.filter(user=request.user, resolved_at__isnull=True).update(resolved_at=timezone.now())
        return Response({'status': 'all notifications marked as read'}, status=status.HTTP_200_OK)
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        from django.utils import timezone
        alert = self.get_object()
        alert.resolved_at = timezone.now()
        alert.save()
        return Response({'status': 'notification marked as read'})