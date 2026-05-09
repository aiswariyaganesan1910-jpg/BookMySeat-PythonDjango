from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [

    path('', views.home, name='home'),

    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='users/login.html'
        ),
        name='login'
    ),

    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='users/reset_password.html'
        ),
        name='password_reset'
    ),

    path(
        'password-reset-done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='users/password_reset_done.html'
        ),
        name='password_reset_done'
    ),

]