from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("mytimescale", "0004_compress"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                """
                ALTER TABLE public.device_ospm
                    ADD COLUMN IF NOT EXISTS flow DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS code VARCHAR(64);
                """
            ],
            reverse_sql=[
                """
                ALTER TABLE public.device_ospm
                    DROP COLUMN IF EXISTS flow,
                    DROP COLUMN IF EXISTS code;
                """
            ],
        ),
    ]
