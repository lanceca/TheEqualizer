from django.urls import path

from . import views


urlpatterns = [

    path(
        "create/",
        views.create_article,
        name="create_article",
    ),

    # =========================
    # SUBMISSIONS
    # =========================

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

    # =========================
    # DRAFTS
    # =========================

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

    # =========================
    # PUBLISHED ARTICLES
    # =========================

    path(
        "published/",
        views.published_articles,
        name="published_articles",
    ),

    # Article version history
    # EIC, Editor, and Staff only for now.

    path(
        "articles/<int:article_id>/history/",
        views.article_version_history,
        name="article_version_history",
    ),

    path(
        "articles/<int:article_id>/history/<int:version_number>/",
        views.article_version_detail,
        name="article_version_detail",
    ),

    # EIC direct article management

    path(
        "articles/<int:article_id>/edit-direct/",
        views.edit_published_article,
        name="edit_published_article",
    ),

    path(
        "articles/<int:article_id>/archive-direct/",
        views.archive_own_published_article,
        name="archive_own_published_article",
    ),

    # =========================
    # EDIT REQUESTS
    # =========================

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

    # =========================
    # DELETION REQUESTS
    # =========================

    path(
        "articles/<int:article_id>/request-deletion/",
        views.request_article_deletion,
        name="request_article_deletion",
    ),

    path(
        "deletion-requests/mine/",
        views.my_deletion_requests,
        name="my_deletion_requests",
    ),

    path(
        "deletion-requests/<int:request_id>/review/",
        views.review_deletion_request,
        name="review_deletion_request",
    ),

    path(
        "deletion-requests/",
        views.eic_deletion_requests,
        name="eic_deletion_requests",
    ),

    # =========================
    # STAFF CONTENT REPORTS
    # =========================

    path(
        "articles/<int:article_id>/report/",
        views.report_article_content,
        name="report_article_content",
    ),

    path(
        "content-reports/mine/",
        views.my_content_reports,
        name="my_content_reports",
    ),

    path(
        "content-reports/<int:report_id>/cancel/",
        views.cancel_content_report,
        name="cancel_content_report",
    ),

    path(
        "content-reports/<int:report_id>/resolve/",
        views.resolve_content_report,
        name="resolve_content_report",
    ),

    path(
        "content-reports/<int:report_id>/require-revision/",
        views.require_revision_from_report,
        name="require_revision_from_report",
    ),

    path(
        "content-reports/",
        views.eic_content_reports,
        name="eic_content_reports",
    ),

    # =========================
    # ARCHIVE
    # =========================

    path(
        "archive/",
        views.archived_articles,
        name="archived_articles",
    ),

    path(
        "archive/<int:article_id>/restore/",
        views.restore_archived_article,
        name="restore_archived_article",
    ),

]