from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from .decorators import role_required
from .forms import (
    AdminCreateDistributorForm,
    AdminRegistrationForm,
    AdminTicketReplyForm,
    DistributorRegistrationForm,
    DistributorSearchForm,
    EmailLoginForm,
    ForgotPasswordForm,
    OTPVerifyForm,
    ResetPasswordForm,
    StyledPasswordChangeForm,
    SupportTicketForm,
    UserProfileForm,
)
from .models import AuditLog, LoginActivity, OTPVerification, SupportTicket
from .utils import (
    create_audit,
    create_login_activity,
    create_password_reset_otp,
    send_account_status_email,
    send_otp_email,
    send_password_changed_email,
)

User = get_user_model()


def _store_dev_otp_for_console_backend(request, otp):
    if settings.DEBUG and settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
        request.session['dev_reset_otp'] = otp
    else:
        request.session.pop('dev_reset_otp', None)


def _safe_send_reset_otp(request, user, otp):
    try:
        send_otp_email(user, otp, request)
        return True
    except Exception as exc:
        if settings.DEBUG:
            request.session['dev_email_error'] = str(exc)
        return False


def _record_failed_login(request, role):
    email = request.POST.get('email', '').lower().strip()
    user = User.objects.filter(email__iexact=email).first()
    status = LoginActivity.Status.FAILED
    message = 'Invalid login attempt.'
    if user and not user.is_locked:
        user.register_failed_login()
    if user and user.is_locked:
        status = LoginActivity.Status.LOCKED
        message = 'Account locked after multiple failed login attempts.'
    create_login_activity(request, email, status, user=user, role=role, message=message)


def home(request):
    if request.user.is_authenticated:
        if request.user.role == User.Role.ADMIN:
            return redirect('admin_dashboard')
        return redirect('distributor_dashboard')
    return render(request, 'accounts/home.html')


def register_admin(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = AdminRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Admin account created successfully. Please login.')
        return redirect('admin_login')
    return render(request, 'accounts/register.html', {'form': form, 'title': 'Admin Registration', 'role': 'Admin'})


def register_distributor(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = DistributorRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        create_audit(None, 'Distributor registration submitted', f'{user.email} registered and is pending approval.', target=user, request=request)
        messages.success(request, 'Distributor account created. Your account is pending admin approval.')
        return redirect('distributor_login')
    return render(request, 'accounts/register.html', {'form': form, 'title': 'Distributor Registration', 'role': 'Distributor'})


def login_admin(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = EmailLoginForm(request.POST or None, role=User.Role.ADMIN)
    if request.method == 'POST':
        if form.is_valid():
            user = form.cleaned_data['user']
            user.reset_login_security()
            create_login_activity(request, user.email, LoginActivity.Status.SUCCESS, user=user, role=user.role, message='Admin logged in.')
            login(request, user)
            messages.success(request, 'Logged in successfully.')
            return redirect('admin_dashboard')
        _record_failed_login(request, User.Role.ADMIN)
    return render(request, 'accounts/login.html', {'form': form, 'title': 'Admin Login', 'role': 'Admin', 'forgot_url': reverse('forgot_password', args=['admin'])})


def login_distributor(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = EmailLoginForm(request.POST or None, role=User.Role.DISTRIBUTOR)
    if request.method == 'POST':
        if form.is_valid():
            user = form.cleaned_data['user']
            user.reset_login_security()
            create_login_activity(request, user.email, LoginActivity.Status.SUCCESS, user=user, role=user.role, message='Distributor logged in.')
            login(request, user)
            messages.success(request, 'Logged in successfully.')
            return redirect('distributor_dashboard')
        _record_failed_login(request, User.Role.DISTRIBUTOR)
    return render(request, 'accounts/login.html', {'form': form, 'title': 'Distributor Login', 'role': 'Distributor', 'forgot_url': reverse('forgot_password', args=['distributor'])})


@login_required
def logout_view(request):
    create_audit(request.user, 'Logout', 'User logged out.', target=request.user, request=request)
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('home')


@login_required
@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    distributors = User.objects.filter(role=User.Role.DISTRIBUTOR)
    context = {
        'total_distributors': distributors.count(),
        'pending_distributors': distributors.filter(status=User.Status.PENDING).count(),
        'approved_distributors': distributors.filter(status=User.Status.APPROVED).count(),
        'blocked_distributors': distributors.filter(status=User.Status.BLOCKED).count(),
        'failed_logins': LoginActivity.objects.filter(status__in=[LoginActivity.Status.FAILED, LoginActivity.Status.LOCKED]).count(),
        'open_tickets': SupportTicket.objects.exclude(status=SupportTicket.Status.CLOSED).count(),
        'recent_logins': LoginActivity.objects.select_related('user')[:8],
        'recent_tickets': SupportTicket.objects.select_related('distributor')[:5],
    }
    return render(request, 'accounts/admin_dashboard.html', context)


@login_required
@role_required(User.Role.DISTRIBUTOR)
def distributor_dashboard(request):
    tickets = request.user.support_tickets.all()
    return render(request, 'accounts/distributor_dashboard.html', {
        'profile_completion': request.user.profile_completion,
        'open_tickets': tickets.exclude(status=SupportTicket.Status.CLOSED).count(),
        'recent_tickets': tickets[:5],
    })


@login_required
@role_required(User.Role.ADMIN)
def distributor_list(request):
    form = DistributorSearchForm(request.GET or None)
    distributors = User.objects.filter(role=User.Role.DISTRIBUTOR)
    if form.is_valid():
        q = form.cleaned_data.get('q')
        status = form.cleaned_data.get('status')
        if q:
            distributors = distributors.filter(Q(full_name__icontains=q) | Q(email__icontains=q) | Q(username__icontains=q) | Q(company_name__icontains=q))
        if status:
            distributors = distributors.filter(status=status)
    return render(request, 'accounts/distributor_list.html', {'form': form, 'distributors': distributors})


@login_required
@role_required(User.Role.ADMIN)
def distributor_detail(request, user_id):
    distributor = get_object_or_404(User, id=user_id, role=User.Role.DISTRIBUTOR)
    return render(request, 'accounts/distributor_detail.html', {'distributor': distributor, 'tickets': distributor.support_tickets.all()[:5], 'logins': distributor.login_activities.all()[:8]})


@login_required
@role_required(User.Role.ADMIN)
def distributor_action(request, user_id, action):
    distributor = get_object_or_404(User, id=user_id, role=User.Role.DISTRIBUTOR)
    if request.method != 'POST':
        return redirect('distributor_detail', user_id=distributor.id)
    actions = {
        'approve': User.Status.APPROVED,
        'reject': User.Status.REJECTED,
        'block': User.Status.BLOCKED,
        'activate': User.Status.APPROVED,
    }
    if action == 'delete':
        email = distributor.email
        distributor.delete()
        create_audit(request.user, 'Deleted distributor', f'Deleted distributor {email}.', request=request)
        messages.success(request, 'Distributor deleted successfully.')
        return redirect('distributor_list')
    if action not in actions:
        messages.error(request, 'Invalid action.')
        return redirect('distributor_detail', user_id=distributor.id)
    distributor.status = actions[action]
    distributor.is_active = action != 'block'
    distributor.save(update_fields=['status', 'is_active'])
    status_label = distributor.get_status_display()
    send_account_status_email(distributor, status_label)
    create_audit(request.user, f'{action.title()} distributor', f'{distributor.email} status changed to {status_label}.', target=distributor, request=request)
    messages.success(request, f'Distributor status updated to {status_label}.')
    return redirect('distributor_detail', user_id=distributor.id)


@login_required
@role_required(User.Role.ADMIN)
def create_distributor(request):
    form = AdminCreateDistributorForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        distributor = form.save()
        create_audit(request.user, 'Created distributor', f'Admin created distributor {distributor.email}.', target=distributor, request=request)
        send_account_status_email(distributor, 'Approved')
        messages.success(request, 'Distributor created and approved successfully.')
        return redirect('distributor_detail', user_id=distributor.id)
    return render(request, 'accounts/create_distributor.html', {'form': form})


@login_required
@role_required(User.Role.ADMIN)
def login_activity(request):
    activities = LoginActivity.objects.select_related('user')[:100]
    return render(request, 'accounts/login_activity.html', {'activities': activities})


@login_required
@role_required(User.Role.ADMIN)
def audit_logs(request):
    logs = AuditLog.objects.select_related('actor', 'target')[:100]
    return render(request, 'accounts/audit_logs.html', {'logs': logs})


def forgot_password(request, role):
    role_map = {'admin': User.Role.ADMIN, 'distributor': User.Role.DISTRIBUTOR}
    if role not in role_map:
        messages.error(request, 'Invalid password reset page.')
        return redirect('home')
    form = ForgotPasswordForm(request.POST or None, role=role_map[role])
    if request.method == 'POST' and form.is_valid():
        user = form.user
        otp, otp_obj = create_password_reset_otp(user)
        sent = _safe_send_reset_otp(request, user, otp)
        _store_dev_otp_for_console_backend(request, otp)
        request.session['reset_user_id'] = user.id
        request.session['reset_role'] = role
        request.session['otp_verified'] = False
        create_audit(None, 'Password reset OTP requested', f'OTP requested for {user.email}.', target=user, request=request)
        if sent:
            messages.success(request, 'OTP sent to your registered email.')
        else:
            messages.error(request, 'Email sending failed. In DEBUG mode, use the OTP shown on the verification page or check SMTP settings.')
        return redirect('verify_otp')
    return render(request, 'accounts/forgot_password.html', {'form': form, 'role': role.title()})


def verify_otp(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Password reset session expired. Please start again.')
        return redirect('home')
    user = get_object_or_404(User, id=user_id)
    form = OTPVerifyForm(request.POST or None, user=user)
    if request.method == 'POST' and form.is_valid():
        form.otp_obj.is_verified = True
        form.otp_obj.save(update_fields=['is_verified'])
        request.session['otp_verified'] = True
        create_audit(None, 'Password reset OTP verified', f'OTP verified for {user.email}.', target=user, request=request)
        messages.success(request, 'OTP verified. Create your new password.')
        return redirect('reset_password')
    return render(request, 'accounts/verify_otp.html', {
        'form': form,
        'email': user.email,
        'dev_otp': request.session.get('dev_reset_otp') if settings.DEBUG else None,
        'dev_email_error': request.session.get('dev_email_error') if settings.DEBUG else None,
    })


def resend_otp(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Password reset session expired. Please start again.')
        return redirect('home')
    user = get_object_or_404(User, id=user_id)
    otp, otp_obj = create_password_reset_otp(user)
    sent = _safe_send_reset_otp(request, user, otp)
    _store_dev_otp_for_console_backend(request, otp)
    request.session['otp_verified'] = False
    create_audit(None, 'Password reset OTP resent', f'OTP resent for {user.email}.', target=user, request=request)
    if sent:
        messages.success(request, 'A new OTP has been sent to your email.')
    else:
        messages.error(request, 'Email sending failed. In DEBUG mode, use the OTP shown on the verification page or check SMTP settings.')
    return redirect('verify_otp')


def reset_password(request):
    user_id = request.session.get('reset_user_id')
    otp_verified = request.session.get('otp_verified')
    if not user_id or not otp_verified:
        messages.error(request, 'Please verify OTP before resetting password.')
        return redirect('home')
    user = get_object_or_404(User, id=user_id)
    form = ResetPasswordForm(user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        OTPVerification.objects.filter(user=user, purpose=OTPVerification.Purpose.PASSWORD_RESET).delete()
        role = request.session.get('reset_role')
        for key in ['reset_user_id', 'reset_role', 'otp_verified', 'dev_reset_otp', 'dev_email_error']:
            request.session.pop(key, None)
        send_password_changed_email(user)
        create_audit(None, 'Password reset completed', f'Password reset completed for {user.email}.', target=user, request=request)
        messages.success(request, 'Password reset successfully. Please login again.')
        if role == 'admin':
            return redirect('admin_login')
        return redirect('distributor_login')
    return render(request, 'accounts/reset_password.html', {'form': form})


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


@login_required
def edit_profile(request):
    form = UserProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        create_audit(request.user, 'Profile updated', 'User updated profile information.', target=request.user, request=request)
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')
    return render(request, 'accounts/edit_profile.html', {'form': form})


@login_required
def change_password(request):
    form = StyledPasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        send_password_changed_email(user)
        create_audit(request.user, 'Password changed', 'User changed password from profile.', target=request.user, request=request)
        messages.success(request, 'Password changed successfully.')
        return redirect('profile')
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def support_tickets(request):
    if request.user.role == User.Role.ADMIN:
        tickets = SupportTicket.objects.select_related('distributor').all()
    else:
        tickets = request.user.support_tickets.all()
    return render(request, 'accounts/support_tickets.html', {'tickets': tickets})


@login_required
@role_required(User.Role.DISTRIBUTOR)
def create_ticket(request):
    form = SupportTicketForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        ticket = form.save(commit=False)
        ticket.distributor = request.user
        ticket.save()
        create_audit(request.user, 'Support ticket created', f'Ticket #{ticket.id}: {ticket.subject}', target=request.user, request=request)
        messages.success(request, 'Support ticket submitted successfully.')
        return redirect('support_ticket_detail', ticket_id=ticket.id)
    return render(request, 'accounts/create_ticket.html', {'form': form})


@login_required
def support_ticket_detail(request, ticket_id):
    if request.user.role == User.Role.ADMIN:
        ticket = get_object_or_404(SupportTicket, id=ticket_id)
        form = AdminTicketReplyForm(request.POST or None, instance=ticket)
        if request.method == 'POST' and form.is_valid():
            updated = form.save(commit=False)
            updated.replied_by = request.user
            updated.save()
            create_audit(request.user, 'Support ticket updated', f'Ticket #{ticket.id} updated.', target=ticket.distributor, request=request)
            messages.success(request, 'Ticket updated successfully.')
            return redirect('support_ticket_detail', ticket_id=ticket.id)
    else:
        ticket = get_object_or_404(SupportTicket, id=ticket_id, distributor=request.user)
        form = None
    return render(request, 'accounts/support_ticket_detail.html', {'ticket': ticket, 'form': form})
