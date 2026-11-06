from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("publications", "0028_add_literary_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="peopleprofile",
            name="image_position_x",
            field=models.PositiveSmallIntegerField(
                default=50,
                help_text="Horizontal focal position of the profile image (0–100%).",
                validators=[MinValueValidator(0), MaxValueValidator(100)],
            ),
        ),
        migrations.AddField(
            model_name="peopleprofile",
            name="image_position_y",
            field=models.PositiveSmallIntegerField(
                default=50,
                help_text="Vertical focal position of the profile image (0–100%).",
                validators=[MinValueValidator(0), MaxValueValidator(100)],
            ),
        ),
    ]
