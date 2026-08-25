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

    path(
        "drafts/",
        views.my_drafts,
        name="my_drafts",
    ),

    path(
        "drafts/<int:article_id>/edit/",
        views.edit_draft,
        name="edit_draft",
    ),

    path(
        "drafts/<int:article_id>/delete/",
        views.delete_draft,
        name="delete_draft",
    ),

    path(
        "published/",
        views.published_articles,
        name="published_articles",
    ),

    path(
        "articles/<int:article_id>/request-edit/",
        views.request_article_edit,
        name="request_article_edit",
    ),

    path(
        "edit-requests/mine/",
        views.my_edit_requests,
        name="my_edit_requests",
    ),

    path(
        "edit-requests/<int:request_id>/review/",
        views.review_edit_request,
        name="review_edit_request",
    ),

    path(
        "edit-requests/",
        views.eic_edit_requests,
        name="eic_edit_requests",
    ),
]