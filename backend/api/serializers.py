from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from django.db import transaction
from .models import User, EmergencyContact, PasswordResetCode, TherapistProfile, Favorite,AvailabilitySlot,ExploreItem,ExploreCategory,Report,FAQ,ContactMessage,Session,Medicine,MoodLog,PatientOnboardingSurvey,Alert,ReportType,ContactCategory
from django.contrib.auth.hashers import check_password
from django.utils import timezone
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    mobile_phone = serializers.CharField(required=True)
    emergency_contact_phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    gender = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'password', 'password2',
            'gender', 'mobile_phone', 'emergency_contact_phone'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
            'gender': {'required': True},
        }
        
    def validate_gender(self, value):
        gender_map = {
            'Male': 'M', 'Female': 'F', 'Other': 'O',
            'male': 'M', 'female': 'F', 'M': 'M', 'F': 'F'
        }
        normalized_value = gender_map.get(value, value)
        valid_choices = [choice[0] for choice in User.GENDER_CHOICES]
        if normalized_value not in valid_choices:
            raise serializers.ValidationError("Invalid gender choice.")
        return normalized_value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('password2', None)
        emergency_phone = validated_data.pop('emergency_contact_phone', None)
        
        user = User.objects.create_user(
            username=validated_data['email'], 
            **validated_data
        )

        if emergency_phone:
            EmergencyContact.objects.create(
                user=user,
                phone=emergency_phone
            )
        return user
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        data['user'] = user
        return data


class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Ensure user exists
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email address.")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        try:
           
            reset_code = PasswordResetCode.objects.filter(code=data['code']).latest('created_at')
        except PasswordResetCode.DoesNotExist:
            raise serializers.ValidationError({"code": "Invalid verification code."})
        if not reset_code.is_valid():
            raise serializers.ValidationError({"code": "Verification code has expired."})
        data['reset_code'] = reset_code
        return data


class TherapistListSerializer(serializers.ModelSerializer):
    # profile_image = serializers.ImageField(source='user.profile_image', read_only=True) 
    profile_image = serializers.CharField( read_only=True)                      #Added By Mohamed Walid
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = TherapistProfile
        fields = [
            'id',
            'name',
            'specialization',
            'location',
            'avg_rating',
            'review_count',
            'profile_image',
            'is_favorited'
        ]

    def get_is_favorited(self, obj):
        request = self.context.get('request')

        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user,
                therapist=obj
            ).exists()

        return False

class AvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilitySlot
        fields = ['id', 'date', 'start_time', 'is_booked']

class TherapistDetailSerializer(serializers.ModelSerializer):
    # profile_image = serializers.ImageField(source='user.profile_image', read_only=True)
    profile_image = serializers.CharField( read_only=True)                        #Added By Mohamed Walid
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    is_favorited = serializers.SerializerMethodField()
    patients_count = serializers.SerializerMethodField()
    years_of_experience = serializers.SerializerMethodField()
    class Meta:
        model = TherapistProfile
        fields = [
            'id', 'name', 'specialization', 'location', 'bio_summary', 
            'years_of_experience', 'patients_count', 'avg_rating', 
            'review_count', 'hourly_rate', 'profile_image', 'is_favorited'
        ]
    def get_years_of_experience(self, obj):
        return f"{obj.years_of_experience} Yrs"
    def get_patients_count(self, obj):
        if obj.patients_count >= 500:
            return "500+"
        elif obj.patients_count >= 100:
            return "100+"
        elif obj.patients_count >= 50:
            return "50+"
        else:
            return str(obj.patients_count)

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user, therapist=obj).exists()
        return False



class BookingConfirmationSerializer(serializers.Serializer):
    slot_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        required=True, 
        min_length=1
    )
    cardholder_name = serializers.CharField(required=True)
    card_number = serializers.CharField(required=True, min_length=16, max_length=19)
    expiry_date = serializers.CharField(required=True, help_text="MM/YY")
    cvv = serializers.CharField(required=True, min_length=3, max_length=4)
    save_info = serializers.BooleanField(required=False, default=False)

    def validate_slot_ids(self, value):
        return value
    def validate_expiry_date(self, value):
        from datetime import datetime
        try:
            exp_date = datetime.strptime(value, "%m/%y")
            if exp_date < datetime.now():
                raise serializers.ValidationError("Card has expired.")
        except ValueError:
            raise serializers.ValidationError("Invalid date format. Use MM/YY.")
        return value
class TherapistDashboardSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.get_full_name', default="Unknown Patient", read_only=True)
    patient_image = serializers.ImageField(source='patient.profile_image', read_only=True)
    age = serializers.SerializerMethodField() # لازم يتعرف هنا
    payment_info = serializers.SerializerMethodField()

    class Meta:
        model = AvailabilitySlot
        fields = ['id', 'patient_name', 'patient_image', 'age', 'date', 'start_time', 'payment_info']

    def get_age(self, obj):
        if obj.patient and obj.patient.birthday:
            import datetime
            return (datetime.date.today() - obj.patient.birthday).days // 365
        return "N/A"

    def get_payment_info(self, obj):
        if not obj.patient:
            return None
            
        from .models import Payment
        payment = Payment.objects.filter(patient=obj.patient, therapist=obj.therapist).last()
        if payment:
            return {
                "amount": payment.amount,
                "transaction_id": payment.transaction_id,
                "status": payment.status,
                "date": payment.created_at.strftime("%d %b %Y")
            }
        return None
class SessionSerializer(serializers.ModelSerializer):
    therapist_name = serializers.CharField(source='therapist.get_full_name', read_only=True)
    therapist_image = serializers.ImageField(source='therapist.profile_image', read_only=True)
    specialization = serializers.CharField(source='therapist.therapist_profile.specialization', read_only=True)
    
    display_date = serializers.SerializerMethodField()
    display_time = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'session_id', 'therapist_name', 'therapist_image', 'specialization',
            'session_date', 'display_date', 'display_time', 
            'meeting_link', 
            'status',
            'progress_level', 'attendance', 'report'
        ]

    def get_display_date(self, obj):
        from django.utils import timezone
        import datetime
        today = timezone.now().date()
        if obj.session_date.date() == today:
            return "Today"
        elif obj.session_date.date() == today + datetime.timedelta(days=1):
            return "Tomorrow"
        return obj.session_date.strftime("%d %b")

    def get_display_time(self, obj):
        return obj.session_date.strftime("%I:%M %p")
class MedicineSerializer(serializers.ModelSerializer):
    patient_id = serializers.IntegerField(write_only=True)
    reminder_text = serializers.SerializerMethodField()

    class Meta:
        model = Medicine
        fields = [
            'id',
            'name',
            'dosage',
            'frequency',
            'scheduled_time',
            'start_date',
            'end_date',
            'is_active',
            'notes',
            'reminder_text',
            'patient_id'
        ]
        read_only_fields = ['id']

    def get_reminder_text(self, obj):
        if obj.scheduled_time:
            return f"Take {obj.name} at {obj.scheduled_time}"
        return f"Take {obj.name}"

    def create(self, validated_data):
        request = self.context['request']

        patient_id = validated_data.pop('patient_id')

        return Medicine.objects.create(
            patient_id=patient_id,
            prescribed_by=request.user,
            **validated_data
        )
class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ['id', 'user', 'therapist', 'created_at']
        read_only_fields = ['user', 'created_at']
class ExploreItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExploreItem
        fields = ['id', 'title', 'external_url', 'image', 'duration']

class ExploreCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExploreCategory
        fields = ['id', 'title', 'description', 'icon', 'category_type']



class UserAccountUpdateSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(write_only=True, required=False)
    new_password = serializers.CharField(write_only=True, required=False)
    confirm_new_password = serializers.CharField(write_only=True, required=False)
    emergency_phone = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'mobile_phone', 'profile_image', 
            'old_password', 'new_password', 'confirm_new_password',
            'emergency_phone' 
        ]

    def validate(self, data):
        new_pw = data.get('new_password')
        confirm_pw = data.get('confirm_new_password')
        old_pw = data.get('old_password')

        if new_pw:
           
            if not old_pw:
                raise serializers.ValidationError({"old_password": "Old password is required to set a new one."})
            
           
            if not check_password(old_pw, self.instance.password):
                raise serializers.ValidationError({"old_password": "Old password is incorrect."})

         
            if new_pw != confirm_pw:
                raise serializers.ValidationError({"confirm_new_password": "New passwords do not match."})
        
        return data

    def update(self, instance, validated_data):
      
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.mobile_phone = validated_data.get('mobile_phone', instance.mobile_phone)
        
        if 'profile_image' in validated_data:
            instance.profile_image = validated_data['profile_image']

        if validated_data.get('new_password'):
            instance.set_password(validated_data['new_password'])
        
        instance.save()

       
        emergency_phone = validated_data.get('emergency_phone')
        if emergency_phone:
            contact, created = EmergencyContact.objects.get_or_create(user=instance)
            contact.phone = emergency_phone
            contact.save()

        return instance
class ReportSerializer(serializers.ModelSerializer):
    primary_issue = serializers.PrimaryKeyRelatedField(queryset=ReportType.objects.all())

    class Meta:
        model = Report
        fields = ['id', 'primary_issue', 'details', 'created_at']
        read_only_fields = ['id', 'created_at']

class ContactMessageSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=ContactCategory.objects.all())

    class Meta:
        model = ContactMessage
        fields = ['id', 'category', 'message', 'screenshot', 'created_at']
        read_only_fields = ['id', 'created_at']


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ['id', 'question', 'answer']

class MoodLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoodLog
        fields = ['id', 'mood_type', 'note', 'created_at']
        read_only_fields = ['id', 'created_at']

class UserHomeSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_mood = serializers.SerializerMethodField()
    weekly_status = serializers.SerializerMethodField()
    recommendations = serializers.SerializerMethodField()
    motivation_video = serializers.SerializerMethodField()

    def get_last_mood(self, obj):
        today = timezone.now().date()
       
        mood = MoodLog.objects.filter(user=obj, created_at__date=today).first()
        if mood:
            return MoodLogSerializer(mood).data
        return None

    def get_weekly_status(self, obj):
        
        moods = MoodLog.objects.filter(user=obj).order_by('-created_at')[:7]
        
        if not moods:
            return "No data this week. Start tracking!"
        
        happy_count = sum(1 for m in moods if m.mood_type in ["happy", "joyful"])
        if happy_count >= 4:
            return "You've been happier this week. Keep going! 💪"
        return "Take some time for yourself today ❤️"

    def get_motivation_video(self, obj):
            videos = ExploreItem.objects.filter(category__category_type='video')
            
            if videos.exists():
                import random
                random_video = random.choice(list(videos))
                
                return {
                    "id": random_video.id,
                    "category_name": random_video.category.title,
                    "title": random_video.title,
                    "url": random_video.external_url,
                    "image": random_video.image.url if random_video.image else None,
                    "duration": random_video.duration
                }
            return None
# http://127.0.0.1:8000/api/home/mood_history/
    def get_recommendations(self, obj):
        return [
            {"title": "AI Chatbot", "desc": "24/7 AI-powered support chat", "icon": "sparkles"},
            {"title": "Find Therapist", "desc": "Search and book professional sessions", "icon": "search"},
            {"title": "Mood Tracking", "desc": "Track your emotional patterns", "icon": "chart"}
        ]
class PatientSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientOnboardingSurvey
        fields = [
            'traumatic_experience', 
            'life_status', 
            'mindset', 
            'daily_rhythm', 
            'account_status'
        ]

    def validate(self, attrs):
        if not any(attrs.values()):
            raise serializers.ValidationError("You must answer at least one question.")
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        survey, created = PatientOnboardingSurvey.objects.update_or_create(
            user=user,
            defaults=validated_data
        )
        return survey
    

class NotificationSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    icon_type = serializers.ReadOnlyField(source='type')

    class Meta:
        model = Alert
        fields = [
            'alert_id', 'title', 'message', 'type', 
            'icon_type', 'time_ago', 'created_at', 'resolved_at'
        ]

    def get_title(self, obj):
        titles = {
            'risk': 'Wellness Check',
            'medication': 'Medication Reminder',
            'appointment': 'Upcoming Session',
            'emergency': '🚨 Emergency Alert',
            'payment': 'Payment Successful',
        }
        return titles.get(obj.type, 'Notification')

    def get_time_ago(self, obj):
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = (diff.seconds // 60) % 60
        if minutes > 0:
            return f"{minutes}m ago"
        return "Just now"


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct.")
        return value
        
    def validate(self, data):
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        old_password = data.get('old_password')

        if new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "New passwords do not match."})
            
        if old_password == new_password:
            raise serializers.ValidationError({"new_password": "New password cannot be the same as the old password."})
            
        return data