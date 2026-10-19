from django.db.models import Count


def status_tabs(queryset, selected, choices):
    """Tab data for a status-filtered list, plus the queryset narrowed to `selected`.

    Counts come from `queryset` as given, so they reflect the other filters and
    add up to "All". Returns (tabs, selected, narrowed_queryset).
    """
    counts = {r["status"]: r["n"] for r in queryset.values("status").annotate(n=Count("id")).order_by()}
    counts["all"] = sum(counts.values())

    valid = {value for value, _ in choices}
    selected = selected if selected in valid else "all"
    tabs = [
        {"id": value, "label": label, "count": counts.get(value, 0), "active": value == selected}
        for value, label in [("all", "All"), *choices]
    ]
    narrowed = queryset if selected == "all" else queryset.filter(status=selected)
    return tabs, selected, narrowed


def filter_params(request, *drop):
    """Query string of the current filters, minus `page` and anything in `drop`."""
    params = request.GET.copy()
    for key in ("page", *drop):
        params.pop(key, None)
    return params.urlencode()
