from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_systemupdate_systemupdatereceipt"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("SUBMISSION", "Submission"),
                    ("EDIT_REQUEST", "Edit Request"),
                    ("DELETION_REQUEST", "Deletion Request"),
                    ("ARCHIVE_RECOMMENDATION", "Archive Recommendation"),
                    ("CONTENT_REPORT", "Content Report"),
                    ("REVISION", "Revision"),
                    ("GENERAL", "General"),
                ],
                default="GENERAL",
                max_length=30,
            ),
        ),
    ]
