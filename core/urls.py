from django.urls import re_path

from . import views

urlpatterns = [
    re_path('telegram_hook/?', views.telegram_hook, name='telegram_hook')
]
