from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('create/', views.create_request, name='create_request'),
    path('update/<int:request_id>/', views.update_status, name='update_status'),
    path('timeline/<int:request_id>/', views.request_timeline, name='timeline'),
]
