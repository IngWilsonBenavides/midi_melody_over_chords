"""Django admin for the MIDI Curator application."""
from django.contrib import admin

from .models import MidiItem, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    search_fields = ["name"]


@admin.register(MidiItem)
class MidiItemAdmin(admin.ModelAdmin):
    list_display = [
        "name", "source_type", "rating", "approved", "favorite",
        "tag_list", "file_missing", "updated_at",
    ]
    list_filter = ["source_type", "approved", "favorite", "file_missing", "tags"]
    search_fields = ["name", "filename", "notes"]
    filter_horizontal = ["tags"]
    readonly_fields = ["file_path", "filename", "created_at", "updated_at"]

    @admin.display(description="Tags")
    def tag_list(self, obj):
        return ", ".join(t.name for t in obj.tags.all())
