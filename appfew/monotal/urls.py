from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('register/form/', views.register_form, name='register_form'),
    path('register/complete/', views.register_complete, name='register_complete'),
    path('register/sent/', views.register_sent, name='register_sent'),
    path('verify/<uuid:token>/', views.email_verify, name='email_verify'),
    path('profile/', views.profile, name='profile'),
    path('sell/', views.create_sell, name='create_sell'),
]