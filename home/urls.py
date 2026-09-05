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
    # PEOPLE & TEAMS
    # ======================================================

    path(
        "people/",
        views.people_and_teams,
        name="people_and_teams",
    ),

    path(
        "api/people/",
        views.people_and_teams_api,
        name="people_and_teams_api",
    ),

    # ======================================================
    # ABOUT US
    # ======================================================

    path(
        "about-us/",
        views.about_us,
        name="about_us",
    ),


    # ======================================================
    # ARTICLE CATEGORIES
    # ======================================================

    path(
        "category/<slug:category_slug>/",
        views.category_articles,
        name="category_articles",
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
    # SCHOOL UPDATES
    # ======================================================

    path(
        "school-updates/",
        views.school_updates,
        name="school_updates",
    ),

    path(
        "school-updates/<slug:slug>/",
        views.school_advertisement_detail,
        name="school_advertisement_detail",
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
