from datetime import timedelta
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from .models import AuditLog, LoginActivity, OTPVerification


def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def create_audit(actor, action, description='', target=None, request=None):
    return AuditLog.objects.create(
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        target=target,
        action=action,
        description=description,
        ip_address=get_client_ip(request) if request else None,
    )


def create_login_activity(request, email, status, user=None, role='', message=''):
    return LoginActivity.objects.create(
        email=(email or '').lower().strip(),
        user=user,
        role=role or (user.role if user else ''),
        status=status,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:1000],
        message=message[:255],
    )


def create_password_reset_otp(user):
    OTPVerification.objects.filter(user=user, purpose=OTPVerification.Purpose.PASSWORD_RESET).delete()
    plain_otp = OTPVerification.generate_otp()
    otp_obj = OTPVerification.objects.create(
        user=user,
        otp=make_password(plain_otp),
        purpose=OTPVerification.Purpose.PASSWORD_RESET,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    return plain_otp, otp_obj


def send_html_email(subject, template_base, context, recipients):
    text_body = render_to_string(f'emails/{template_base}.txt', context)
    html_body = render_to_string(f'emails/{template_base}.html', context)
    email = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, recipients)
    email.attach_alternative(html_body, 'text/html')
    email.send(fail_silently=False)
    return True


def send_otp_email(user, otp, request=None):
    context = {
        'user': user,
        'otp': otp,
        'expires_minutes': 5,
        'site_name': 'Secure User Authentication System',
    }
    return send_html_email('Your Password Reset OTP', 'password_reset', context, [user.email])


def send_account_status_email(user, status_label):
    subject = f'Your distributor account is {status_label}'
    message = f'Hello {user.full_name}, your distributor account status is now {status_label}.'
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)


def send_password_changed_email(user):
    subject = 'Your password was changed'
    message = f'Hello {user.full_name}, your password was changed successfully. If this was not you, contact support immediately.'
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
