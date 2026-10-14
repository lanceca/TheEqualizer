from django.db import migrations


def add_literary_category(apps, schema_editor):
    Category = apps.get_model("publications", "Category")

    by_slug = Category.objects.filter(slug="literary").first()
    if by_slug is not None:
        if (
            by_slug.name != "Literary"
            and not Category.objects.filter(name="Literary")
            .exclude(pk=by_slug.pk)
            .exists()
        ):
            by_slug.name = "Literary"
            by_slug.save(update_fields=["name"])
        return

    by_name = Category.objects.filter(name="Literary").first()
    if by_name is not None:
        by_name.slug = "literary"
        by_name.save(update_fields=["slug"])
        return

    Category.objects.create(
        name="Literary",
        slug="literary",
    )


def remove_literary_category(apps, schema_editor):
    Category = apps.get_model("publications", "Category")
    Category.objects.filter(
        name="Literary",
        slug="literary",
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("publications", "0027_archiverecommendation"),
    ]

    operations = [
        migrations.RunPython(
            add_literary_category,
            remove_literary_category,
        ),
    ]
