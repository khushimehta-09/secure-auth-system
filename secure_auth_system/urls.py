from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def home(request):
    return HttpResponse("🚀 Django is LIVE on Render")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home),   # TEMP HOME (GUARANTEED WORKING)
    path('', include('accounts.urls')),
]