"""DRF serializers for the MIDI Curator API."""
from rest_framework import serializers

from .models import MidiItem, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class MidiItemListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    tags = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = MidiItem
        fields = [
            "id",
            "name",
            "filename",
            "source_type",
            "file_url",
            "duration_seconds",
            "rating",
            "approved",
            "favorite",
            "tags",
            "notes",
            "file_missing",
            "created_at",
            "updated_at",
        ]

    def get_file_url(self, obj: MidiItem) -> str:
        request = self.context.get("request")
        path = f"/api/midis/{obj.pk}/stream/"
        if request:
            return request.build_absolute_uri(path)
        return path


class MidiItemDetailSerializer(MidiItemListSerializer):
    """Full serializer including all fields (same as list for now)."""


class FeedbackSerializer(serializers.ModelSerializer):
    """PATCH payload for curator feedback."""

    # Accept tag names; auto-create tags that don't exist yet
    tags = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = MidiItem
        fields = ["rating", "approved", "favorite", "tags", "notes"]
        extra_kwargs = {
            "rating":   {"required": False, "allow_null": True},
            "approved": {"required": False, "allow_null": True},
            "favorite": {"required": False},
            "notes":    {"required": False},
        }

    def update(self, instance: MidiItem, validated_data: dict) -> MidiItem:
        tag_names = validated_data.pop("tags", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tag_names is not None:
            tag_objects = []
            for name in tag_names:
                tag, _ = Tag.objects.get_or_create(name=name.lower().strip())
                tag_objects.append(tag)
            instance.tags.set(tag_objects)

        return instance
