import publications.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "publications",
            "0025_workflow_review_attribution",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="peopleprofile",
            name="image",
            field=models.ImageField(
                blank=True,
                upload_to="people_profiles/",
                validators=[
                    publications.validators.validate_article_image,
                ],
            ),
        ),
    ]
