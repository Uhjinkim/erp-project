from decimal import Decimal

from rest_framework import serializers


class VacationRequestInputSerializer(serializers.Serializer):
    type_id = serializers.CharField(max_length=20)
    start_datetime = serializers.DateTimeField()
    end_datetime = serializers.DateTimeField()
    use_days = serializers.DecimalField(max_digits=3, decimal_places=2, min_value=Decimal("0.01"))
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, allow_blank=False)
