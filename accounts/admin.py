from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AuditLog, CustomUser, LoginActivity, OTPVerification, SupportTicket


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'username', 'full_name', 'role', 'status', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('role', 'status', 'is_active', 'is_staff')
    search_fields = ('email', 'username', 'full_name', 'company_name')
    ordering = ('-date_joined',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'username', 'role', 'status', 'phone', 'company_name', 'address', 'city', 'state', 'country', 'profile_image')}),
        ('Login security', {'fields': ('failed_login_attempts', 'lockout_until')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'full_name', 'role', 'status', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'purpose', 'created_at', 'expires_at', 'is_verified')
    list_filter = ('purpose', 'is_verified')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('otp', 'created_at')


@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'role', 'status', 'ip_address', 'created_at')
    list_filter = ('status', 'role')
    search_fields = ('email', 'user__full_name', 'ip_address')
    readonly_fields = ('email', 'user', 'role', 'status', 'ip_address', 'user_agent', 'message', 'created_at')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'actor', 'target', 'ip_address', 'created_at')
    search_fields = ('action', 'description', 'actor__email', 'target__email')
    readonly_fields = ('actor', 'target', 'action', 'description', 'ip_address', 'created_at')


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'distributor', 'priority', 'status', 'created_at', 'updated_at')
    list_filter = ('priority', 'status')
    search_fields = ('subject', 'message', 'distributor__email')
