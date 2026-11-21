from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("mytimescale", "0005_ospm_flow_code"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                """
                ALTER TABLE public.device_ospm
                    ALTER COLUMN code TYPE smallint
                    USING (
                        CASE
                            WHEN code IS NULL OR btrim(code) = '' THEN NULL
                            ELSE btrim(code)::smallint
                        END
                    );
                ALTER TABLE public.device_ospm
                    RENAME COLUMN code TO error_code;
                """
            ],
            reverse_sql=[
                """
                ALTER TABLE public.device_ospm
                    RENAME COLUMN error_code TO code;
                ALTER TABLE public.device_ospm
                    ALTER COLUMN code TYPE varchar(64)
                    USING (
                        CASE
                            WHEN code IS NULL THEN NULL
                            ELSE code::text
                        END
                    );
                """
            ],
        ),
    ]
