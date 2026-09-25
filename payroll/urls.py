from django.urls import path

from . import views

app_name = 'payroll'

urlpatterns = [
    path('', views.run_list, name='run_list'),  # placeholder until Phase 3
]
