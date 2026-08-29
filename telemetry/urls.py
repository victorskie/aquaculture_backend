from django.urls import path
from . import views

urlpatterns = [
    # This creates the route ending in /upload/
    path('upload/', views.upload_data, name='upload_data'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # This creates the lightweight health check route
    path('ping/', views.ping, name='ping'),
]