from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_co_authors_to_contributors(apps, schema_editor):
    Article = apps.get_model(
        "publications",
        "Article",
    )

    ArticleContributor = apps.get_model(
        "publications",
        "ArticleContributor",
    )

    Submission = apps.get_model(
        "publications",
        "Submission",
    )

    # ======================================================
    # EXISTING ARTICLE CO-AUTHORS
    # ======================================================

    for article in Article.objects.all():

        display_order = 0

        for co_author in article.co_authors.all():

            # The primary author should not also be
            # duplicated as a contributor.
            if co_author.id == article.author_id:
                continue

            ArticleContributor.objects.get_or_create(
                article_id=article.id,
                user_id=co_author.id,
                role="CO_WRITER",
                defaults={
                    "display_order": display_order,
                },
            )

            display_order += 1

    # ======================================================
    # EXISTING SUBMISSION SNAPSHOTS
    # ======================================================

    for submission in Submission.objects.all():

        old_co_authors = (
            submission.snapshot_co_authors
            or []
        )

        contributors = []

        for index, username in enumerate(
            old_co_authors
        ):
            contributors.append(
                {
                    "user_id": None,
                    "username": username,
                    "role": "CO_WRITER",
                    "role_display": "Co-Writer",
                    "display_order": index,
                }
            )

        submission.snapshot_contributors = (
            contributors
        )

        submission.save(
            update_fields=[
                "snapshot_contributors",
            ]
        )


def reverse_contributors_to_co_authors(
    apps,
    schema_editor,
):
    Article = apps.get_model(
        "publications",
        "Article",
    )

    Submission = apps.get_model(
        "publications",
        "Submission",
    )

    # ======================================================
    # RESTORE ARTICLE CO-AUTHORS
    # ======================================================

    for article in Article.objects.all():

        article.co_authors.clear()

        contributors = (
            article.contributors
            .all()
            .order_by(
                "display_order",
                "id",
            )
        )

        for contributor in contributors:

            if (
                contributor.role
                == "CO_WRITER"
            ):
                article.co_authors.add(
                    contributor.user_id
                )

    # ======================================================
    # RESTORE SNAPSHOT CO-AUTHORS
    # ======================================================

    for submission in Submission.objects.all():

        contributors = (
            submission.snapshot_contributors
            or []
        )

        co_authors = []

        for contributor in contributors:

            if (
                contributor.get("role")
                == "CO_WRITER"
            ):
                username = (
                    contributor.get("username")
                )

                if username:
                    co_authors.append(
                        username
                    )

        submission.snapshot_co_authors = (
            co_authors
        )

        submission.save(
            update_fields=[
                "snapshot_co_authors",
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            "publications",
            "0016_article_co_authors_article_excerpt_and_more",
        ),
        migrations.swappable_dependency(
            settings.AUTH_USER_MODEL
        ),
    ]

    operations = [

        migrations.CreateModel(
            name="ArticleContributor",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            (
                                "CO_WRITER",
                                "Co-Writer",
                            ),
                            (
                                "PHOTOGRAPHER",
                                "Photographer",
                            ),
                            (
                                "PHOTOJOURNALIST",
                                "Photojournalist",
                            ),
                            (
                                "CARTOONIST",
                                "Cartoonist",
                            ),
                            (
                                "ILLUSTRATOR",
                                "Illustrator",
                            ),
                            (
                                "VIDEOGRAPHER",
                                "Videographer",
                            ),
                            (
                                "VIDEO_EDITOR",
                                "Video Editor",
                            ),
                            (
                                "LAYOUT_ARTIST",
                                "Layout Artist",
                            ),
                            (
                                "RESEARCHER",
                                "Researcher",
                            ),
                            (
                                "CONTRIBUTOR",
                                "Contributor",
                            ),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "display_order",
                    models.PositiveIntegerField(
                        default=0,
                    ),
                ),
                (
                    "article",
                    models.ForeignKey(
                        on_delete=(
                            django.db.models.deletion.CASCADE
                        ),
                        related_name="contributors",
                        to="publications.article",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=(
                            django.db.models.deletion.PROTECT
                        ),
                        related_name="article_contributions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": [
                    "display_order",
                    "id",
                ],
            },
        ),

        migrations.AddConstraint(
            model_name="articlecontributor",
            constraint=models.UniqueConstraint(
                fields=(
                    "article",
                    "user",
                    "role",
                ),
                name=(
                    "unique_article_contributor_role"
                ),
            ),
        ),

        migrations.AddField(
            model_name="submission",
            name="snapshot_contributors",
            field=models.JSONField(
                blank=True,
                default=list,
            ),
        ),

        migrations.RunPython(
            migrate_co_authors_to_contributors,
            reverse_contributors_to_co_authors,
        ),
    ]