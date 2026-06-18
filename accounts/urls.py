from django.urls import path
from . import views

urlpatterns = [
    path('register/admin/', views.register_admin),
    path('login/admin/', views.login_admin),
]