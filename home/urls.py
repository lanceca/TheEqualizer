from django.urls import path

from . import views


urlpatterns = [

    # ======================================================
    # HOME
    # ======================================================

    path(
        "",
        views.home,
        name="home",
    ),


    # ======================================================
    # PUBLIC ARTICLES
    # ======================================================

    path(
        "articles/<slug:slug>/",
        views.article_detail,
        name="article_detail",
    ),

    path(
        "articles/<slug:slug>/download-pdf/",
        views.download_article_pdf,
        name="download_article_pdf",
    ),

    path(
        "articles/<slug:slug>/react/",
        views.react_to_article,
        name="react_to_article",
    ),

    path(
        "articles/<slug:slug>/share/",
        views.share_article,
        name="share_article",
    ),



    # ======================================================
    # DIGITAL PUBLICATIONS
    # ======================================================

    path(
        "digital-publications/",
        views.digital_publications,
        name="digital_publications",
    ),

    path(
        "digital-publications/<slug:slug>/",
        views.digital_publication_detail,
        name="digital_publication_detail",
    ),

    path(
        "api/digital-publications/<slug:slug>/",
        views.digital_publication_api,
        name="digital_publication_api",
    ),

]
