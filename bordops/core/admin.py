from django.contrib import admin


class AdminScopedMixin:
    scope_fk_fields = {
        "ship_id": "ship",
        "service_id": "service",
        "sector_id": "sector",
        "section_id": "section",
    }

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        profile = getattr(request.user, "profile", None)
        if not profile:
            return qs
        level, obj_id = profile.scope
        if not level:
            return qs
        field = f"{level}_id"
        if hasattr(qs.model, field):
            return qs.filter(**{field: obj_id})
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        profile = getattr(request.user, "profile", None)
        if profile:
            level, obj_id = profile.scope
            if level:
                target_field = self.scope_fk_fields.get(f"{level}_id")
                if db_field.name == target_field:
                    kwargs["queryset"] = db_field.related_model.objects.filter(id=obj_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
