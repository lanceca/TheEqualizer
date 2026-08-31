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
        "articles/<slug:slug>/react/",
        views.react_to_article,
        name="react_to_article",
    ),

    path(
        "articles/<slug:slug>/share/",
        views.share_article,
        name="share_article",
    ),

]