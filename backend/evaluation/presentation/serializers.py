from rest_framework import serializers


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
