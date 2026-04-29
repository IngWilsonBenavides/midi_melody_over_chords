"""Data models for the MIDI Curator application.

MidiItem  – one MIDI file on disk, with curator feedback.
Tag       – free-form genre/style tag, reused across items.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Tag(models.Model):
    """A reusable genre/style label (e.g. "rock", "blues", "jazz")."""

    name = models.CharField(max_length=100, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class MidiItem(models.Model):
    """Represents a single MIDI file discovered on disk."""

    class SourceType(models.TextChoices):
        DATASET = "dataset", "Dataset"
        GENERATED = "generated", "Generated"

    # ── File identity ─────────────────────────────────────────────────────────
    name = models.CharField(max_length=255, db_index=True)
    filename = models.CharField(max_length=255)
    # Relative path from MIDI_MEDIA_ROOT (e.g. "dataset/happy_melody.mid")
    file_path = models.CharField(max_length=500, unique=True, db_index=True)
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.DATASET,
        db_index=True,
    )
    duration_seconds = models.FloatField(
        null=True, blank=True,
        help_text="Duration in seconds, populated on scan when possible.",
    )
    file_missing = models.BooleanField(
        default=False,
        help_text="True when the file was present previously but is now missing.",
    )

    # ── Human feedback ────────────────────────────────────────────────────────
    rating = models.IntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Curator rating 1–10.",
    )
    # Tri-state: null=not reviewed, True=approved, False=rejected
    approved = models.BooleanField(
        null=True, blank=True,
        help_text="null=not reviewed, true=approved, false=rejected.",
    )
    favorite = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Marked as a favourite.",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="midi_items")
    notes = models.TextField(blank=True, help_text="Free-text curator notes.")

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_type", "name"]

    def __str__(self) -> str:
        return f"{self.source_type}/{self.name}"
