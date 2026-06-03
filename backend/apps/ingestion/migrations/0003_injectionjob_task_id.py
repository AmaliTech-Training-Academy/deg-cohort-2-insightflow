from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ingestion", "0002_injectionjob"),
    ]

    operations = [
        migrations.AddField(
            model_name="injectionjob",
            name="task_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
