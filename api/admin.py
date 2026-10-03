"""DRF API root, versioning and shared serializers.

Admin registration is added per model as that model lands, not in bulk ahead of
it. Registering a model that does not exist yet raises at import, and a
placeholder `ModelAdmin` with no `list_display` renders an unusable list.
"""
