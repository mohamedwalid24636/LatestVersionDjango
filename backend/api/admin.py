from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (User, 
                     TherapistProfile, 
                     Favorite, 
                     EmergencyContact, 
                     UserPhone, 
                     AvailabilitySlot,
                     ExploreCategory,
                     ExploreItem,
                     PatientTherapist,
                     Alert,
                     AlertMedicine,
                     Session,
                     Medicine,
                     PatientOnboardingSurvey,
                     Message,
                     Conversation,
                     Report,
                     MoodLog,
                     ContactMessage,
                     FAQ,
                     ReportType,
                     ContactCategory,
                     )

class AvailabilitySlotInline(admin.TabularInline):
    model = AvailabilitySlot
    extra = 3
    fields = ('date', 'start_time', 'is_booked')

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['email', 'username', 'role', 'gender', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('role', 'gender', 'mobile_phone', 'birthday', 'profile_image')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Extra Info', {'fields': ('role', 'gender', 'mobile_phone', 'email')}),
    )

@admin.register(TherapistProfile)
class TherapistProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'patients_count', 'avg_rating')
    search_fields = ('user__first_name', 'user__last_name', 'specialization')
    inlines = [AvailabilitySlotInline]

@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ('therapist', 'date', 'start_time', 'is_booked')
    list_filter = ('therapist', 'date', 'is_booked')
    search_fields = ('therapist__user__first_name', 'therapist__user__last_name')
    ordering = ('date', 'start_time')
@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('alert_id', 'user', 'type', 'message', 'created_at')
    list_filter = ('type', 'created_at')

@admin.register(AlertMedicine)
class AlertMedicineAdmin(admin.ModelAdmin):
    list_display = ('alert', 'medicine')


class ExploreItemInline(admin.TabularInline):
    model = ExploreItem
    extra = 1 

@admin.register(ExploreCategory)
class ExploreCategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'category_type')
    search_fields = ('title',)
    inlines = [ExploreItemInline]

@admin.register(ExploreItem)
class ExploreItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'duration')
    list_filter = ('category',)

admin.site.register(User, CustomUserAdmin)
admin.site.register(Favorite)
admin.site.register(EmergencyContact)
admin.site.register(UserPhone)
admin.site.register(PatientTherapist)
admin.site.register(Session)
admin.site.register(Medicine)
admin.site.register(PatientOnboardingSurvey)
admin.site.register(Message)
admin.site.register(Conversation)
admin.site.register(Report),
admin.site.register(FAQ),
admin.site.register(ContactMessage),
admin.site.register(MoodLog),
admin.site.register(ReportType),
admin.site.register(ContactCategory),