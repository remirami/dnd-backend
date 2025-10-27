from django.urls import path
from .views import import_monsters_view

urlpatterns = [
    path('enemies/import/', import_monsters_view, name='import_monsters'),
]