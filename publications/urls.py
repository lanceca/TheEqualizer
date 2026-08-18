from django.urls import path

from . import views


urlpatterns = [
    path(
        "create/",
        views.create_article,
        name="create_article",
    ),

    path(
        "submissions/pending/",
        views.pending_submissions,
        name="pending_submissions",
    ),

    path(
    "submissions/<int:submission_id>/review/",
    views.review_submission,
    name="review_submission",
    ),

]