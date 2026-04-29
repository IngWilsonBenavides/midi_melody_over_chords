"""Management command: scan MIDI media directories and upsert DB records.

Usage:
    python manage.py scan_midis

Walks MIDI_MEDIA_ROOT/dataset/ and MIDI_MEDIA_ROOT/generated/,
creating or updating a MidiItem record for each .mid/.midi file found.

Files already in the DB but no longer on disk are marked as file_missing=True
(feedback is preserved).
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from midi_curator.models import MidiItem


class Command(BaseCommand):
    help = "Scan MIDI_MEDIA_ROOT sub-directories and sync MidiItem records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--media-root",
            default=None,
            help="Override the MIDI_MEDIA_ROOT setting.",
        )

    def handle(self, *args, **options):
        media_root = Path(options["media_root"] or settings.MIDI_MEDIA_ROOT)

        if not media_root.exists():
            self.stderr.write(
                self.style.WARNING(f"MIDI_MEDIA_ROOT does not exist: {media_root}")
            )
            return

        found_paths: set[str] = set()
        created = updated = 0

        for source_type in ("dataset", "generated"):
            scan_dir = media_root / source_type
            if not scan_dir.exists():
                self.stdout.write(
                    f"  Directory {scan_dir} not found — skipping {source_type}."
                )
                continue

            midi_files = sorted(
                list(scan_dir.rglob("*.mid")) + list(scan_dir.rglob("*.midi"))
            )
            self.stdout.write(
                f"  [{source_type}] found {len(midi_files)} file(s) in {scan_dir}"
            )

            for midi_file in midi_files:
                relative_path = str(midi_file.relative_to(media_root))
                found_paths.add(relative_path)
                name = midi_file.stem

                # Try to read duration
                duration_seconds = None
                try:
                    import mido

                    mid = mido.MidiFile(str(midi_file))
                    duration_seconds = round(mid.length, 3)
                except Exception:
                    pass  # duration stays null — not critical

                obj, was_created = MidiItem.objects.update_or_create(
                    file_path=relative_path,
                    defaults={
                        "name": name,
                        "filename": midi_file.name,
                        "source_type": source_type,
                        "duration_seconds": duration_seconds,
                        "file_missing": False,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        # Mark DB items whose files have disappeared
        disappeared = (
            MidiItem.objects.filter(file_missing=False)
            .exclude(file_path__in=found_paths)
            .update(file_missing=True)
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Scan complete — created: {created}, "
                f"updated: {updated}, "
                f"marked missing: {disappeared}"
            )
        )
