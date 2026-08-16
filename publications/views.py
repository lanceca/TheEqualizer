from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .models import Article, ArticleAttachment, Category, Tag

@login_required
def create_article(request):

    if request.user.role != "EDITOR":
        return redirect("dashboard")

    categories = Category.objects.all()
    tags = Tag.objects.all()

    if request.method == "POST":

        title = request.POST.get("title")
        category_id = request.POST.get("category")
        content = request.POST.get("content")
        tag_ids = request.POST.getlist("tags")

        featured_image = request.FILES.get("featured_image")
        attachments = request.FILES.getlist("attachments")

        category = Category.objects.get(id=category_id)

        article = Article.objects.create(
            title=title,
            slug=title.lower().replace(" ", "-"),
            category=category,
            author=request.user,
            content=content,
            featured_image=featured_image,
        )

        article.tags.set(tag_ids)
        
        for image in attachments:
            ArticleAttachment.objects.create(
                article=article,
                image=image
            )

        return redirect("dashboard")

    return render(
        request,
        "publications/create_article.html",
        {
            "categories": categories,
            "tags": tags,
        }
    )