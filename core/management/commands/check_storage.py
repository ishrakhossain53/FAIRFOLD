"""Round-trip a tiny object through whatever storage backend is configured.

Run it after `docker compose up -d --wait` to answer the only question that
matters about an object store: can this application actually write and read an
object right now? A green container health check answers a different question —
MinIO can be healthy while Django points at the wrong bucket, the wrong
credentials or the wrong endpoint.

    docker compose exec django python manage.py check_storage

The probe is deleted afterwards. Nothing here touches candidate data.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from core import storage


class Command(BaseCommand):
    help = "Write, read back and delete a small probe object in the default storage."

    def handle(self, *args, **options) -> None:
        try:
            result = storage.round_trip()
        except storage.StorageError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"storage round-trip verified: backend={result.backend} "
                f"bucket={result.bucket} key={result.key} bytes={result.size}"
            )
        )
