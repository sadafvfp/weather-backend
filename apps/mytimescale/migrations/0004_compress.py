from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mytimescale", "0003_refresh"),
    ]
    operations = [
        migrations.RunSQL(
            sql=["""
                        ALTER TABLE device_ospm
                        SET (
	                    timescaledb.compress,
	                    timescaledb.compress_segmentby='device_id',
	                    timescaledb.compress_orderby='created_datetime'
                        );
                        SELECT add_compression_policy('device_ospm', INTERVAL '6 months');

                        ALTER MATERIALIZED VIEW hourly_ospm set (timescaledb.compress = true);
                        ALTER MATERIALIZED VIEW hourly_ospm_temp set (timescaledb.compress = true);
                        ALTER MATERIALIZED VIEW daily_ospm set (timescaledb.compress = true);
                        ALTER MATERIALIZED VIEW daily_ospm_temp set (timescaledb.compress = true);

                        SELECT add_compression_policy('hourly_ospm', INTERVAL '5 years');
                        SELECT add_compression_policy('hourly_ospm_temp', INTERVAL '5 years');
                        SELECT add_compression_policy('daily_ospm', INTERVAL '5 years');
                        SELECT add_compression_policy('daily_ospm_temp', INTERVAL '5 years');


                """],
            reverse_sql=[" SELECT remove_compression_policy('hourly_ospm');\
                  SELECT remove_compression_policy('hourly_ospm_temp');\
                  SELECT remove_compression_policy('daily_ospm');\
                  SELECT remove_compression_policy('daily_ospm_temp');\
                  SELECT remove_compression_policy('device_ospm');\
                  SELECT decompress_chunk(c, true) FROM show_chunks('device_ospm') c;\
                "],
        )
    ]
