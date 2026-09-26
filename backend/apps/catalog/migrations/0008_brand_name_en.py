"""Latin brand name, so «بوش» and «BOSCH» are the same brand to search."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("catalog", "0007_rarepartrequest_quantity")]

    operations = [
        migrations.AddField(
            model_name="brand",
            name="name_en",
            field=models.CharField(blank=True, max_length=120, verbose_name="نام انگلیسی"),
        ),
    ]
