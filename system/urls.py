from django.urls import path

from .views import health, system_info, system_metrics, system_resources


urlpatterns = [
    path('health/', health, name='system-health'),
    path('metrics/', system_metrics, name='system-metrics'),
    path('resources/', system_resources, name='system-resources'),
    path('info/', system_info, name='system-info'),
]
