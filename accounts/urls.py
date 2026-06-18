from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/admin/', views.register_admin, name='admin_register'),
    path('register/distributor/', views.register_distributor, name='distributor_register'),
    path('login/admin/', views.login_admin, name='admin_login'),
    path('login/distributor/', views.login_distributor, name='distributor_login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/distributor/', views.distributor_dashboard, name='distributor_dashboard'),
    path('admin/distributors/', views.distributor_list, name='distributor_list'),
    path('admin/distributors/create/', views.create_distributor, name='create_distributor'),
    path('admin/distributors/<int:user_id>/', views.distributor_detail, name='distributor_detail'),
    path('admin/distributors/<int:user_id>/<str:action>/', views.distributor_action, name='distributor_action'),
    path('admin/login-activity/', views.login_activity, name='login_activity'),
    path('admin/audit-logs/', views.audit_logs, name='audit_logs'),
    path('forgot-password/<str:role>/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('support/', views.support_tickets, name='support_tickets'),
    path('support/create/', views.create_ticket, name='create_ticket'),
    path('support/<int:ticket_id>/', views.support_ticket_detail, name='support_ticket_detail'),
]
