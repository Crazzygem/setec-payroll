from django.urls import path

from . import views

app_name = 'payroll'

urlpatterns = [
    path('', views.run_list, name='run_list'),
    path('new/', views.run_create, name='run_create'),
    path('payslip/<int:payslip_pk>/', views.payslip_view, name='payslip_view'),
    path('payslip/<int:payslip_pk>/update/', views.payslip_update, name='payslip_update'),
    path('<int:pk>/export/csv/', views.export_csv, name='export_csv'),
    path('<int:pk>/export/xlsx/', views.export_xlsx, name='export_xlsx'),
    path('<int:pk>/', views.run_detail, name='run_detail'),
    path('<int:pk>/finalize/', views.run_finalize, name='run_finalize'),
    path('<int:pk>/extras/', views.run_extras_update, name='run_extras_update'),
    path('<int:pk>/regenerate/', views.run_regenerate, name='run_regenerate'),
    path('<int:pk>/delete/', views.run_delete, name='run_delete'),
]
