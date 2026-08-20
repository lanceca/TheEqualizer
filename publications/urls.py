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

    path(
    "submissions/mine/",
    views.my_submissions,
    name="my_submissions",
    ),

    path(
    "submissions/<int:submission_id>/revise/",
    views.revise_submission,
    name="revise_submission",
    ),

    path(
    "submissions/resubmitted/",
    views.resubmitted_submissions,
    name="resubmitted_submissions",
    ),

]