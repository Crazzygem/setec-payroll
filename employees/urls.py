from django.urls import path

from . import views

app_name = 'employees'

urlpatterns = [
    path('', views.employee_list, name='list'),
    path('new/', views.employee_create, name='create'),
    path('<int:pk>/edit/', views.employee_edit, name='edit'),
    path('<int:pk>/delete/', views.employee_delete, name='delete'),
    path('<int:pk>/deactivate/', views.employee_deactivate, name='deactivate'),
    path('departments/', views.department_list, name='department_list'),
    path('departments/new/', views.department_create, name='department_create'),
    path('departments/<int:pk>/edit/', views.department_update,
         name='department_update'),
    path('departments/<int:pk>/delete/', views.department_delete,
         name='department_delete'),
    path('positions/', views.position_list, name='position_list'),
    path('positions/new/', views.position_create, name='position_create'),
    path('positions/<int:pk>/edit/', views.position_update,
         name='position_update'),
    path('positions/<int:pk>/delete/', views.position_delete,
         name='position_delete'),
]
