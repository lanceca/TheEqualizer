from django.urls import path

from . import views


app_name = "audit"


urlpatterns = [
    path(
        "",
        views.action_log_view,
        name="action_log",
    ),
    path(
        "data/",
        views.action_log_data,
        name="action_log_data",
    ),
]
