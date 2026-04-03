from .scopes import scope_filters_for_user

class ScopedQuerySetMixin:
    scope_fields_order = ["ship_id", "service_id", "sector_id", "section_id"]

    def get_scoped_filters(self):
        return scope_filters_for_user(self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        filters = self.get_scoped_filters()
        # Only apply filters that exist on this model
        applicable = {k: v for k, v in filters.items() if hasattr(qs.model, k.replace("_id", ""))}
        if applicable:
            return qs.filter(**applicable)
        return qs
