class AuditMixin:

    def perform_create(self, serializer):
        obj = serializer.save()
        self.audit("CREATE", obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        self.audit("UPDATE", obj)

    def perform_destroy(self, instance):
        self.audit("DELETE", instance)
        instance.delete()

    def audit(self, action, obj):
        AuditLog.objects.create(
            user=self.request.user,
            action=action,
            model_name=obj._meta.label,
            object_id=str(obj.pk),
        )
