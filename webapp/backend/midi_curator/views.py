"""API views for the MIDI Curator application."""
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.core.management import call_command
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MidiItem, Tag
from .serializers import (
    MidiItemListSerializer,
    MidiItemDetailSerializer,
    FeedbackSerializer,
    TagSerializer,
)


class MidiItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:   GET  /api/midis/            — paginated list with filters
    detail: GET  /api/midis/{id}/       — single item
    stream: GET  /api/midis/{id}/stream/— serve the .mid file
    feedback: PATCH /api/midis/{id}/feedback/ — update curator feedback
    scan:   POST /api/midis/scan/       — trigger rescan of media directories
    """

    queryset = MidiItem.objects.prefetch_related("tags").order_by("source_type", "name")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MidiItemDetailSerializer
        return MidiItemListSerializer

    # ── Filtering ─────────────────────────────────────────────────────────────
    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        source_type = params.get("source_type")
        if source_type:
            qs = qs.filter(source_type=source_type)

        tag = params.get("tag")
        if tag:
            qs = qs.filter(tags__name__iexact=tag)

        # approved: "true" / "false" / "null"
        approved_param = params.get("approved")
        if approved_param is not None:
            if approved_param.lower() == "true":
                qs = qs.filter(approved=True)
            elif approved_param.lower() == "false":
                qs = qs.filter(approved=False)
            elif approved_param.lower() == "null":
                qs = qs.filter(approved__isnull=True)

        favorite = params.get("favorite")
        if favorite and favorite.lower() == "true":
            qs = qs.filter(favorite=True)

        min_rating = params.get("min_rating")
        if min_rating:
            try:
                qs = qs.filter(rating__gte=int(min_rating))
            except ValueError:
                pass

        search = params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)

        return qs.distinct()

    # ── Stream endpoint ───────────────────────────────────────────────────────
    @action(detail=True, methods=["get"])
    def stream(self, request: Request, pk=None):
        """Serve the .mid file for in-browser playback."""
        item: MidiItem = self.get_object()
        file_path = Path(settings.MIDI_MEDIA_ROOT) / item.file_path

        if not file_path.exists():
            item.file_missing = True
            item.save(update_fields=["file_missing"])
            raise Http404("MIDI file not found on disk.")

        # FileResponse takes ownership of the file handle and closes it after delivery.
        response = FileResponse(
            open(file_path, "rb"),  # noqa: WPS515 — FileResponse closes the handle
            content_type="audio/midi",
        )
        response["Content-Disposition"] = f'inline; filename="{item.filename}"'
        response["Accept-Ranges"] = "bytes"
        response["Access-Control-Allow-Origin"] = "*"
        return response

    # ── Feedback endpoint ─────────────────────────────────────────────────────
    @action(detail=True, methods=["patch"])
    def feedback(self, request: Request, pk=None):
        """Update curator feedback (rating, approved, favorite, tags, notes)."""
        item: MidiItem = self.get_object()
        serializer = FeedbackSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Return the full item after update
        return Response(
            MidiItemDetailSerializer(item, context={"request": request}).data
        )

    # ── Scan endpoint ─────────────────────────────────────────────────────────
    @action(detail=False, methods=["post"])
    def scan(self, request: Request):
        """Trigger a rescan of MIDI_MEDIA_ROOT and return item count."""
        call_command("scan_midis")
        count = MidiItem.objects.count()
        return Response(
            {"status": "ok", "total_items": count},
            status=status.HTTP_200_OK,
        )


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/tags/ — list all available tags."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None  # return all tags (small list)
