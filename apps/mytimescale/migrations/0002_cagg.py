from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False
    dependencies = [
        ("mytimescale", "0001_hypertables"),
    ]
    operations = [
        migrations.RunSQL(
            sql=["""    CREATE MATERIALIZED VIEW hourly_ospm
                        WITH (timescaledb.continuous) AS
                        SELECT time_bucket('1 hour', created_datetime,
                                        origin => TIMESTAMPTZ '2000-01-01 10:00:00+03:30') AS hour,
                            device_id,
                            avg(pm10) AS pm10,
                            min(pm10) AS pm10_min,
                            max(pm10) AS pm10_max,
                            avg(pm25) AS pm25,
                            min(pm25) AS pm25_min,
                            max(pm25) AS pm25_max,
                            avg(temperature) AS temperature,
                            min(temperature) AS temperature_min,
                            max(temperature) AS temperature_max,
                            avg(humidity) AS humidity
                        FROM device_ospm
                        WHERE status=0
                        GROUP BY hour, device_id
                        with no data;

                        CREATE MATERIALIZED VIEW daily_ospm
                        WITH (timescaledb.continuous) AS
                        SELECT time_bucket('1 day', hour,
                                        origin => TIMESTAMPTZ '2000-01-01 10:00:00+03:30') AS day,
                            device_id,
                            avg(pm10) AS pm10,
                            min(pm10_min) AS pm10_min,
                            max(pm10_max) AS pm10_max,
                            avg(pm25) AS pm25,
                            min(pm25_min) AS pm25_min,
                            max(pm25_max) AS pm25_max
                        FROM hourly_ospm
                        GROUP BY day, device_id
                        with no data;

                        CREATE MATERIALIZED VIEW hourly_ospm_temp
                        WITH (timescaledb.continuous) AS
                        SELECT time_bucket('1 hour', created_datetime,origin => TIMESTAMPTZ '2000-01-01 00:00:00+03:30') AS hour,
                            device_id,
                            avg(temperature) AS temperature,
                            min(temperature) AS temperature_min,
                            max(temperature) AS temperature_max,
                            avg(humidity) AS humidity
                        FROM device_ospm
                        WHERE status=0
                        GROUP BY hour, device_id
                        with no data;

                        CREATE MATERIALIZED VIEW daily_ospm_temp
                        WITH (timescaledb.continuous) AS
                        SELECT time_bucket('1 day', hour, origin => TIMESTAMPTZ '2000-01-01 00:00:00+03:30') AS day,
                            device_id,
                            min(temperature_min) AS temperature_min,
                            max(temperature_max) AS temperature_max,
                            avg(humidity) AS humidity
                        FROM hourly_ospm_temp
                        GROUP BY day, device_id
                        with no data;


                        """],
            reverse_sql=["DROP MATERIALIZED VIEW hourly_ospm;\
                    DROP MATERIALIZED VIEW daily_ospm;\
                    DROP MATERIALIZED VIEW hourly_ospm_temp;\
                    DROP MATERIALIZED VIEW daily_ospm_temp;\
                "],
        )
    ]
