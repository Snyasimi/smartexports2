from django.urls import path
from . import views

urlpatterns = [
    path('analyze-label/', views.analyze_fertilizer_label, name='analyze_label'),
    path('', views.index, name='index'),
]