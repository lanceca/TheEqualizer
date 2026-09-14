from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(
            settings.AUTH_USER_MODEL
        ),
        (
            "publications",
            "0024_peopleprofile",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_submissions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="reviewed_by_username",
            field=models.CharField(
                blank=True,
                max_length=150,
            ),
        ),
        migrations.AddField(
            model_name="editrequest",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_edit_requests",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="editrequest",
            name="reviewed_by_username",
            field=models.CharField(
                blank=True,
                max_length=150,
            ),
        ),
        migrations.AddField(
            model_name="deletionrequest",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_deletion_requests",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="deletionrequest",
            name="reviewed_by_username",
            field=models.CharField(
                blank=True,
                max_length=150,
            ),
        ),
        migrations.AddField(
            model_name="contentreport",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_content_reports",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="contentreport",
            name="reviewed_by_username",
            field=models.CharField(
                blank=True,
                max_length=150,
            ),
        ),
    ]
