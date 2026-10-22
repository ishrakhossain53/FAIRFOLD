"""Create the object-storage bucket and its CORS policy (Arch Doc §6.1).

Called from the ``django`` container entrypoint on every start, and safe to run
by hand. Arch Doc §6.1 has no bucket-creation container: a one-shot ``mc`` image
would need its own shell and its own credentials, while this command runs inside
the application with exactly the settings the application uses — so a bucket
created here is a bucket the app can reach.

It is a no-op when ``AWS_STORAGE_BUCKET_NAME`` is unset, because that is a
supported configuration (local filesystem) and not an error.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from core import storage


class Command(BaseCommand):
    help = "Create the S3-compatible bucket and apply its CORS policy. Idempotent."

    def handle(self, *args, **options) -> None:
        if not storage.object_storage_configured():
            self.stdout.write(
                "Object storage is not configured (AWS_STORAGE_BUCKET_NAME "
                "unset); keeping the local filesystem backend."
            )
            return

        try:
            created = storage.ensure_bucket()
            cors = storage.apply_cors()
        except storage.StorageError as exc:
            # CommandError, not the bare exception: the entrypoint runs with
            # `set -e`, and a traceback through boto3 tells an operator nothing
            # they can act on. The message names the operation and the S3 code.
            raise CommandError(str(exc)) from exc

        state = "created" if created else "already present"
        self.stdout.write(
            self.style.SUCCESS(
                f"bucket {storage.bucket_name()} {state}; "
                f"CORS ({len(cors.origins)} origin(s)): {cors.detail}"
            )
        )
        self.stdout.write(f"allowed origins: {', '.join(cors.origins)}")
