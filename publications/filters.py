"""Validated GET filters shared by the public and editorial libraries."""
from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import Category


def filter_article_library(queryset, params, *, date_field="published_at", candidates=False):
    category = params.get("category", "")
    if category.isascii() and category.isdigit() and len(category) <= 19 and int(category) < 2**63:
        queryset = queryset.filter(category_id=int(category))
    for key, lookup in (("start", "gte"), ("end", "lte")):
        try:
            value = parse_date(params.get(key, ""))
        except ValueError:
            value = None
        if value:
            queryset = queryset.filter(**{f"{date_field}__date__{lookup}": value})
    month = params.get("month", "")
    try:
        month_date = parse_date(f"{month}-01") if len(month) == 7 else None
    except ValueError:
        month_date = None
    if month_date:
        queryset = queryset.filter(**{
            f"{date_field}__year": month_date.year,
            f"{date_field}__month": month_date.month,
        })
    if candidates and params.get("older") == "30":
        queryset = queryset.filter(published_at__date__lte=timezone.localdate() - timedelta(days=30))
    return queryset


def library_filter_context(request):
    return {"filter_categories": Category.objects.order_by("name"), "filters": request.GET}
