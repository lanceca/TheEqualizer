from django.db import migrations, models


def validate_existing_emails(
    apps,
    schema_editor,
):
    User = apps.get_model(
        "accounts",
        "User",
    )

    seen = {}

    for user in User.objects.all().only(
        "id",
        "email",
    ):
        normalized = (
            user.email.strip().lower()
            if user.email
            else None
        )

        if not normalized:
            continue

        if normalized in seen:
            raise RuntimeError(
                (
                    "Cannot enable unique account emails because "
                    f"{normalized!r} is used by more than one account "
                    f"(user ids {seen[normalized]} and {user.pk}). "
                    "Resolve the duplicate before running migrate again."
                )
            )

        seen[normalized] = user.pk


def normalize_existing_emails(
    apps,
    schema_editor,
):
    User = apps.get_model(
        "accounts",
        "User",
    )

    for user in User.objects.all().only(
        "id",
        "email",
    ):
        normalized = (
            user.email.strip().lower()
            if user.email
            else None
        )

        User.objects.filter(
            pk=user.pk
        ).update(
            email=normalized
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            "accounts",
            "0002_user_profile_picture",
        ),
    ]

    operations = [
        migrations.RunPython(
            validate_existing_emails,
            migrations.RunPython.noop,
        ),

        migrations.AddField(
            model_name="user",
            name="email_verified",
            field=models.BooleanField(
                default=False,
            ),
        ),

        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                blank=True,
                max_length=254,
                null=True,
                verbose_name="email address",
            ),
        ),

        migrations.RunPython(
            normalize_existing_emails,
            migrations.RunPython.noop,
        ),

        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                blank=False,
                max_length=254,
                null=True,
                unique=True,
                verbose_name="email address",
            ),
        ),
    ]