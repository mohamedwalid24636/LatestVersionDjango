from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import secrets
import string
class User(AbstractUser):
    ROLE_CHOICES = (
        ('patient', 'Patient'),
        ('therapist', 'Therapist'),
        ('admin', 'Admin'),
    )
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    mobile_phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    birthday = models.DateField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
class UserPhone(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='phones')
    phone = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.user.email} - {self.phone}"

class PasswordResetCode(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        expiry = self.created_at + timezone.timedelta(minutes=15)
        return timezone.now() <= expiry

    @classmethod
    def generate_code(cls, email):
        cls.objects.filter(email=email).delete()

        code = ''.join(secrets.choice(string.digits) for _ in range(6))
        return cls.objects.create(email=email, code=code)
    
class TherapistProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='therapist_profile')
    specialization = models.CharField(max_length=255) 
    location = models.CharField(max_length=255, default="Cardiology Clinic") 
    bio_summary = models.TextField(blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)
   
    patients_count = models.PositiveIntegerField(default=0) 
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=60.00) 
    
    avg_rating = models.FloatField(default=0.0)
    review_count = models.PositiveIntegerField(default=0) 
    profile_image = models.CharField(max_length=255, null=True)                                                # Added by Mohamed Walid

    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name}"


class ReportType(models.Model):
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=100, unique=True) 

    def __str__(self):
        return self.name

class Report(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    primary_issue = models.ForeignKey(ReportType, on_delete=models.PROTECT)
    details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class ContactCategory(models.Model):
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class ContactMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(ContactCategory, on_delete=models.PROTECT)
    message = models.TextField()
    screenshot = models.ImageField(upload_to='support_screenshots/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.question

class AvailabilitySlot(models.Model):
    therapist = models.ForeignKey(TherapistProfile, on_delete=models.CASCADE, related_name='availability_slots')
    patient = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='booked_appointments'
    )
    date = models.DateField() 
    start_time = models.TimeField() 
    is_booked = models.BooleanField(default=False)

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        status = "Booked" if self.is_booked else "Available"
        return f"{self.therapist.user.last_name} - {self.date} ({status})"
class Payment(models.Model):
    slot = models.OneToOneField(
        AvailabilitySlot, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='payment'
    )
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    therapist = models.ForeignKey(TherapistProfile, on_delete=models.CASCADE, related_name='payments_received')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, default='Success')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.status}"
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    therapist = models.ForeignKey(TherapistProfile, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'therapist') # Prevents liking the same doctor twice

class PatientTherapist(models.Model):
    """
    Many-to-many relationship between patients and therapists.
    """
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='therapists')
    therapist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patients')
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('patient', 'therapist')

    def __str__(self):
        return f"{self.patient.email} -> {self.therapist.email}"

class Conversation(models.Model):
    """
    A conversation session between a patient and a therapist (or AI).
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('pending', 'Pending'),
    )

    conversation_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    therapist = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='conducted_conversations')

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    summary_text = models.TextField(blank=True)
    mood_classification = models.CharField(max_length=100, blank=True)
    recommended_action = models.TextField(blank=True)
    avg_stress_level = models.FloatField(default=0.0)
    avg_sentiment = models.FloatField(default=0.0)
    avg_risk_level = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation {self.conversation_id} - {self.patient.email}"

class Message(models.Model):
    """
    Individual messages within a conversation.
    """
    SENDER_CHOICES = (
        ('patient', 'Patient'),
        ('therapist', 'Therapist'),
        ('system', 'System'),
    )

    message_id = models.AutoField(primary_key=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        related_name='sent_messages', 
        null=True, 
        blank=True
    )
    sender_type = models.CharField(max_length=20, choices=SENDER_CHOICES)  # can be derived from role, but stored for simplicity

    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()

    # Analysis fields
    sentiment = models.FloatField(default=0.0)
    score = models.FloatField(default=0.0)
    stress_level = models.FloatField(default=0.0)
    risk_level = models.FloatField(default=0.0)
    recommended_action = models.TextField(blank=True)

    def __str__(self):
        return f"Message {self.message_id} in conv {self.conversation.conversation_id}"

class Alert(models.Model):
    ALERT_TYPES = (
        ('risk', 'Risk'),
        ('medication', 'Medication'),
        ('appointment', 'Appointment'),
        ('emergency', 'Emergency'),
        ('payment', 'Payment'),
        ('registration', 'New Registration'),
    )

    alert_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts')
    message = models.TextField()
    type = models.CharField(max_length=20, choices=ALERT_TYPES)
    emergency_contact = models.ForeignKey('EmergencyContact', on_delete=models.SET_NULL, null=True, blank=True, related_name='alerts')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Alert {self.alert_id} for {self.user.email}"

class AlertTime(models.Model):
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='times')
    time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.alert} at {self.time}"
class Medicine(models.Model):
    patient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='patient_medications'
    )
    prescribed_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='doctor_prescriptions'
    )
    name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    scheduled_time = models.TimeField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    instructions = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.patient.email}"
class AlertMedicine(models.Model):
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='medicine_details')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='alerts')

    class Meta:
        unique_together = ('alert', 'medicine')

    def __str__(self):
        return f"Alert {self.alert.alert_id} for {self.medicine.name}"

class Session(models.Model):
    PROGRESS_CHOICES = (
        ('new', 'New'),
        ('ongoing', 'Ongoing'),
        ('stable', 'Stable'),
        ('improving', 'Improving'),
        ('concerning', 'Concerning'),
    )
    
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    session_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    therapist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conducted_sessions')
    meeting_link = models.URLField(max_length=500, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    alert = models.ForeignKey(
        'Alert', 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session_details"
    )

    progress_level = models.CharField(max_length=20, choices=PROGRESS_CHOICES, default='new')
    session_date = models.DateTimeField()
    report = models.TextField(blank=True)
    attendance = models.BooleanField(default=False)

    def __str__(self):
        return f"Session {self.session_id}: {self.patient.get_full_name()} with Dr. {self.therapist.last_name}"
class AlertMessage(models.Model):
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('alert', 'message')

    def __str__(self):
        return f"Alert {self.alert.alert_id} - Message {self.message.message_id}"
class EmergencyContact(models.Model):
    econtact_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=100, blank=True, null=True)
    relation = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return f"Emergency Phone: {self.phone} for {self.user.email}"

class ExploreCategory(models.Model):
    CATEGORY_TYPES = (
        ('video', 'Videos Section'),
        ('game', 'Games Section'),
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.ImageField(upload_to='explore/icons/')
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES, default='video')

    def __str__(self):
        return self.title

class ExploreItem(models.Model):
    category = models.ForeignKey(
        ExploreCategory, 
        related_name='items', 
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=200)
    external_url = models.URLField() 
    image = models.ImageField(upload_to='explore/items/')
    duration = models.CharField(max_length=20, blank=True, null=True) 

    def __str__(self):
        return self.title

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    has_completed_survey = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Patient: {self.user.email}"
class PatientOnboardingSurvey(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='onboarding_data')
    traumatic_experience = models.CharField(max_length=100, blank=True, null=True)
    life_status = models.CharField(max_length=100, blank=True, null=True)
    mindset = models.CharField(max_length=100, blank=True, null=True)
    daily_rhythm = models.CharField(max_length=100, blank=True, null=True)
    account_status = models.CharField(max_length=100, blank=True, null=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Survey results for {self.user.email}"
class BlogPost(models.Model):
    CATEGORY_CHOICES = (
        ('mental_health', 'Mental Health'),
        ('therapist_tips', 'Therapist Tips'),
        ('self_care', 'Self Care'),
        ('research', 'Research'),
    )

    blog_id = models.AutoField(primary_key=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='blog_posts')
    title = models.CharField(max_length=255)
    content = models.TextField()  # merged body and content
    publish_date = models.DateTimeField(default=timezone.now)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='mental_health')
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)

    def __str__(self):
        return self.title


class MoodLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mood_logs')
    mood_type = models.CharField(max_length=50)
    mood_value = models.PositiveSmallIntegerField(editable=False, default=3)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        mood_clean = str(self.mood_type).lower().strip()
        
        if mood_clean in ['joyful', 'joy', 'excited', 'elated', 'happy']:
            self.mood_value = 5
        elif mood_clean in ['relaxed', 'good', 'content', 'pleased']:
            self.mood_value = 4
        elif mood_clean in ['moderate', 'neutral', 'fine', 'calm', 'bored']:
            self.mood_value = 3
        elif mood_clean in ['sad', 'sadness', 'depressed', 'hurt', 'lonely', 'grief']:
            self.mood_value = 2
        elif mood_clean in ['angry', 'anger', 'frustrated', 'anxious', 'fear', 'scared']:
            self.mood_value = 1
        else:
            self.mood_value = 3
            
        super().save(*args, **kwargs)

    @property
    def mood_percentage(self):
        return self.mood_value * 20

    def __str__(self):
        return f"{self.user.username} - {self.mood_type} ({self.mood_value})"