from django.urls import path
from . import views

urlpatterns = [
    # HOME inside app
    path('', views.home, name='home'),

    # AUTH
    path('register/admin/', views.register_admin, name='register_admin'),
    path('register/distributor/', views.register_distributor, name='register_distributor'),

    path('login/admin/', views.login_admin, name='admin_login'),
    path('login/distributor/', views.login_distributor, name='distributor_login'),

    path('logout/', views.logout_view, name='logout'),

    # DASHBOARD
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('distributor/dashboard/', views.distributor_dashboard, name='distributor_dashboard'),
]