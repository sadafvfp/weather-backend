from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mytimescale", "0002_cagg"),
    ]
    operations = [
        migrations.RunSQL(
            sql=["""
                        select add_continuous_aggregate_policy('hourly_ospm',
                        start_offset => INTERVAL '2 day',
                        end_offset => INTERVAL '1 second',
                        schedule_interval => INTERVAL '1 hour',
                        initial_start => '2000-01-01 00:00:01+03:30');

                        select add_continuous_aggregate_policy('hourly_ospm_temp',
                        start_offset => INTERVAL '2 day',
                        end_offset => INTERVAL '1 second',
                        schedule_interval => INTERVAL '1 hour',
                        initial_start => '2000-01-01 00:00:01+03:30');
                        
                        select add_continuous_aggregate_policy('daily_ospm',
                        start_offset => INTERVAL '5 days',
                        end_offset => INTERVAL '2 minutes',
                        schedule_interval => INTERVAL '1 day',
                        initial_start => '2000-01-01 11:02:00+03:30');

                        select add_continuous_aggregate_policy('daily_ospm_temp',
                        start_offset => INTERVAL '5 days',
                        end_offset => INTERVAL '2 minutes',
                        schedule_interval => INTERVAL '1 day',
                        initial_start => '2000-01-01 00:00:02+03:30');




                """],
            reverse_sql=["SELECT remove_continuous_aggregate_policy('hourly_ospm');\
                    SELECT remove_continuous_aggregate_policy('hourly_ospm_temp');\
                    SELECT remove_continuous_aggregate_policy('daily_ospm');\
                    SELECT remove_continuous_aggregate_policy('daily_ospm_temp');\
                    "],
        )
    ]
