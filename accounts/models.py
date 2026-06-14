import secrets
from datetime import timedelta
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, full_name, password=None, role='DISTRIBUTOR', **extra_fields):
        if not email:
            raise ValueError('Email is required.')
        if not username:
            raise ValueError('Username is required.')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, full_name=full_name, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, full_name='System Admin', password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('status', CustomUser.Status.APPROVED)
        return self.create_user(email=email, username=username, full_name=full_name, password=password, role=CustomUser.Role.ADMIN, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        DISTRIBUTOR = 'DISTRIBUTOR', 'Distributor'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        BLOCKED = 'BLOCKED', 'Blocked'

    full_name = models.CharField(max_length=150)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.DISTRIBUTOR)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    phone = models.CharField(max_length=25, blank=True)
    company_name = models.CharField(max_length=180, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True)
    country = models.CharField(max_length=80, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    lockout_until = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name']

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.full_name} ({self.email})'

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN

    @property
    def is_distributor_user(self):
        return self.role == self.Role.DISTRIBUTOR

    @property
    def is_locked(self):
        return bool(self.lockout_until and self.lockout_until > timezone.now())

    @property
    def profile_completion(self):
        fields = [self.full_name, self.username, self.email, self.phone, self.company_name, self.address, self.city, self.state, self.country]
        completed = sum(1 for value in fields if value)
        return int((completed / len(fields)) * 100)

    def reset_login_security(self):
        self.failed_login_attempts = 0
        self.lockout_until = None
        self.save(update_fields=['failed_login_attempts', 'lockout_until'])

    def register_failed_login(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.lockout_until = timezone.now() + timedelta(minutes=10)
        self.save(update_fields=['failed_login_attempts', 'lockout_until'])


class OTPVerification(models.Model):
    class Purpose(models.TextChoices):
        PASSWORD_RESET = 'PASSWORD_RESET', 'Password Reset'
        OTP_VERIFICATION = 'OTP_VERIFICATION', 'OTP Verification'

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='otp_codes')
    otp = models.CharField(max_length=128)
    purpose = models.CharField(max_length=30, choices=Purpose.choices, default=Purpose.PASSWORD_RESET)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    @staticmethod
    def generate_otp():
        return ''.join(secrets.choice('0123456789') for _ in range(6))

    def __str__(self):
        return f'OTP for {self.user.email} - {self.purpose}'


class LoginActivity(models.Model):
    class Status(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        LOCKED = 'LOCKED', 'Locked'

    email = models.EmailField()
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='login_activities')
    role = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Login activities'

    def __str__(self):
        return f'{self.email} - {self.status}'


class AuditLog(models.Model):
    actor = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_actions')
    target = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_targets')
    action = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.action


class SupportTicket(models.Model):
    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        CLOSED = 'CLOSED', 'Closed'

    distributor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=180)
    message = models.TextField()
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    admin_reply = models.TextField(blank=True)
    replied_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='ticket_replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.subject
