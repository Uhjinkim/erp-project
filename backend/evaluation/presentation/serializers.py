from rest_framework import serializers

from evaluation.domain.value_objects import REASON_MAX_LENGTH


class EvaluationCreateSerializer(serializers.Serializer):
    emp_no = serializers.IntegerField()
    eval_year = serializers.RegexField(r"^\d{4}$")
    score = serializers.DecimalField(max_digits=5, decimal_places=2)
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class EvaluationUpdateSerializer(serializers.Serializer):
    score = serializers.DecimalField(max_digits=5, decimal_places=2)
    # Omitted comments keep the stored text, so no default here.
    comments = serializers.CharField(required=False, allow_blank=True)


class EvaluationListQuerySerializer(serializers.Serializer):
    year = serializers.RegexField(r"^\d{4}$", required=False)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=REASON_MAX_LENGTH)


class OptionalReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(
        max_length=REASON_MAX_LENGTH, required=False, allow_blank=True, default=""
    )


class ReassignSerializer(ReasonSerializer):
    evaluator_no = serializers.IntegerField()
