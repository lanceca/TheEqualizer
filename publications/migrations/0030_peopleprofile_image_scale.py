from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("publications", "0029_peopleprofile_image_position"),
    ]

    operations = [
        migrations.AddField(
            model_name="peopleprofile",
            name="image_scale",
            field=models.PositiveSmallIntegerField(
                default=100,
                help_text="Profile image zoom percentage (100–250%).",
                validators=[MinValueValidator(100), MaxValueValidator(250)],
            ),
        ),
    ]
