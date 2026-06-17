from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home(request):
    return HttpResponse("🚀 Django is working on Render!")

urlpatterns = [
    path('', home),  # ROOT URL FIX
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
]