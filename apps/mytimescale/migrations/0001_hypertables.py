from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []
    operations = [
        migrations.RunSQL(
            sql=["""
                        CREATE EXTENSION IF NOT EXISTS timescaledb;
                        CREATE TABLE public.device_ospm (
						created_datetime timestamptz NOT NULL,
						device_id int4,
                        pm10 DOUBLE PRECISION,
                        pm25 DOUBLE PRECISION,
                        temperature DOUBLE PRECISION,
                        humidity DOUBLE PRECISION,
                        status smallint,

                        CONSTRAINT device_ospm_pkey PRIMARY KEY (created_datetime,device_id));
                        SELECT create_hypertable('device_ospm','created_datetime');


                        SELECT set_chunk_time_interval('device_ospm', INTERVAL '6 months');

            """],
            reverse_sql=[" DROP TABLE public.device_sapa;"],
        )
    ]
