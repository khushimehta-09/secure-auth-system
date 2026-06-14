from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import OTPVerification, SupportTicket

User = get_user_model()


BOOTSTRAP_INPUT = {'class': 'form-control'}


class BaseRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}), validators=[validate_password])
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}))

    class Meta:
        model = User
        fields = ['full_name', 'username', 'email', 'password', 'confirm_password']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Email already exists.')
        return email

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Username already exists.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Password and confirm password must match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class AdminRegistrationForm(BaseRegistrationForm):
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.ADMIN
        user.status = User.Status.APPROVED
        user.is_staff = True
        if commit:
            user.save()
        return user


class DistributorRegistrationForm(BaseRegistrationForm):
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.DISTRIBUTOR
        user.status = User.Status.PENDING
        user.is_staff = False
        if commit:
            user.save()
        return user


class AdminCreateDistributorForm(DistributorRegistrationForm):
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone'}))
    company_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company name'}))

    class Meta(DistributorRegistrationForm.Meta):
        fields = ['full_name', 'username', 'email', 'phone', 'company_name', 'password', 'confirm_password']
        widgets = DistributorRegistrationForm.Meta.widgets | {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.status = User.Status.APPROVED
        user.phone = self.cleaned_data.get('phone', '')
        user.company_name = self.cleaned_data.get('company_name', '')
        if commit:
            user.save()
        return user


class EmailLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}))

    def __init__(self, *args, role=None, **kwargs):
        self.role = role
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        if email and password:
            email = email.lower().strip()
            try:
                candidate = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                candidate = None
            if candidate and candidate.is_locked:
                raise ValidationError('Too many failed login attempts. Try again after 10 minutes.')
            user = authenticate(email=email, password=password)
            if user is None:
                raise ValidationError('Invalid email or password.')
            if not user.is_active:
                raise ValidationError('This account is inactive.')
            if self.role and user.role != self.role:
                raise ValidationError(f'This login page is only for {self.role.title()} users.')
            if user.role == User.Role.DISTRIBUTOR and user.status != User.Status.APPROVED:
                raise ValidationError(f'Your distributor account is currently {user.get_status_display()}. Contact admin for access.')
            cleaned_data['user'] = user
        return cleaned_data


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter registered email'}))

    def __init__(self, *args, role=None, **kwargs):
        self.role = role
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise ValidationError('No account found with this email.')
        if self.role and user.role != self.role:
            raise ValidationError(f'This email is not registered as {self.role.title()}.')
        self.user = user
        return email


class OTPVerifyForm(forms.Form):
    otp = forms.CharField(max_length=6, min_length=6, widget=forms.TextInput(attrs={'class': 'form-control otp-input', 'placeholder': 'Enter 6-digit OTP', 'inputmode': 'numeric', 'autocomplete': 'one-time-code'}))

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_otp(self):
        otp = self.cleaned_data['otp'].strip()
        if not otp.isdigit():
            raise ValidationError('OTP must contain only digits.')
        if not self.user:
            raise ValidationError('Password reset session expired. Please request a new OTP.')
        latest = OTPVerification.objects.filter(user=self.user, purpose=OTPVerification.Purpose.PASSWORD_RESET, is_verified=False).first()
        if not latest:
            raise ValidationError('OTP not found. Please request a new OTP.')
        if latest.is_expired():
            latest.delete()
            raise ValidationError('OTP expired. Please request a new OTP.')
        if not check_password(otp, latest.otp):
            raise ValidationError('Invalid OTP.')
        self.otp_obj = latest
        return otp


class ResetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(label='New password', widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password'}), validators=[validate_password])
    new_password2 = forms.CharField(label='Confirm new password', widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}))


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['full_name', 'username', 'email', 'phone', 'company_name', 'address', 'city', 'state', 'country', 'profile_image']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Email already exists.')
        return email

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Username already exists.')
        return username


class StyledPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current password'}))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password'}), validators=[validate_password])
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}))


class DistributorSearchForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search name, email, username, company'}))
    status = forms.ChoiceField(required=False, choices=[('', 'All statuses')] + list(User.Status.choices), widget=forms.Select(attrs={'class': 'form-select'}))


class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ['subject', 'priority', 'message']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ticket subject'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Explain your issue'}),
        }


class AdminTicketReplyForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ['status', 'admin_reply']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'admin_reply': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Reply to distributor'}),
        }
