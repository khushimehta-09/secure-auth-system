from django.urls import path
from . import views
from django.http import HttpResponse

def home(request):
    return HttpResponse("🚀 Django is LIVE on Render")

urlpatterns = [
    path('', home),   # ROOT WORKS HERE
    path('register/admin/', views.register_admin),
    path('login/admin/', views.login_admin),
    path('register/distributor/', views.register_distributor),
    path('login/distributor/', views.login_distributor),
]