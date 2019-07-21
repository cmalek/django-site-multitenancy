from django.urls import path

from .admin import super_admin


urlpatterns = [
    path('root/', super_admin.urls),
]
