from decimal import Decimal

from rest_framework import serializers


class CreateStatementSerializer(serializers.Serializer):
    emp_no = serializers.IntegerField()
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)


class PayrollItemInputSerializer(serializers.Serializer):
    component_code = serializers.CharField(max_length=30)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=Decimal("0"))


class UpdateItemsSerializer(serializers.Serializer):
    items = PayrollItemInputSerializer(many=True)

    def validate_items(self, value: list[dict[str, object]]) -> list[dict[str, object]]:
        if not value:
            raise serializers.ValidationError("급여 구성항목은 최소 1건 이상이어야 합니다.")
        return value


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, allow_blank=False)
