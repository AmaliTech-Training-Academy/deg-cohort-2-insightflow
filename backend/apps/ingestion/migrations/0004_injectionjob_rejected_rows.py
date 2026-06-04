from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ingestion", "0003_injectionjob_task_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="injectionjob",
            name="rejected_rows",
            field=models.IntegerField(default=0),
        ),
    ]
