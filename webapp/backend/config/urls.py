"""URL configuration for the midi_curator project."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("midi_curator.urls")),
]
