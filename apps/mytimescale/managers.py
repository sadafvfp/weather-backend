from django.db.models import Func, Value, DateTimeField
from timescale.db.models.querysets import *


from timescale.db.models.querysets import TimescaleQuerySet
from timescale.db.models.managers import TimescaleManager


class TimeBucketGapFillTZ(Func):
    function = "time_bucket_gapfill"
    output_field = DateTimeField()

    def __init__(self, expression, interval, *, timezone=None, start=None, finish=None):
        self.named = []
        exprs = [Value(interval), expression]
        if timezone:
            exprs.append(Value(timezone))
            self.named.append("timezone")
        if start is not None:
            exprs.append(Value(start))
            self.named.append("start")
        if finish is not None:
            exprs.append(Value(finish))
            self.named.append("finish")
        super().__init__(*exprs, output_field=DateTimeField())

    def as_sql(self, compiler, connection, **extra):
        interval, expr, *rest = self.source_expressions
        isql, ip = compiler.compile(interval)
        esql, ep = compiler.compile(expr)
        sql = [f"{isql}::interval", esql]
        params = [*ip, *ep]
        for name, e in zip(self.named, rest):
            s, p = compiler.compile(e)
            cast = "::text" if name == "timezone" else "::timestamptz"
            sql.append(f"{name} => {s}{cast}")
            params += p
        return f"time_bucket_gapfill({', '.join(sql)})", params


class MyTimescaleQuerySet(TimescaleQuerySet):
    def time_bucket_gapfill(
        self, field, interval, start=None, end=None, timezone=None, **kwargs
    ):
        return self.values(
            bucket=TimeBucketGapFillTZ(
                field, interval, timezone=timezone, start=start, finish=end
            )
        )


class MyTimescaleManager(TimescaleManager):
    def get_queryset(self):
        return MyTimescaleQuerySet(self.model, using=self._db)

    def time_bucket_gapfill(self, *args, **kwargs):
        return self.get_queryset().time_bucket_gapfill(*args, **kwargs)
