from rest_framework import serializers

class SymbolSerializer(serializers.Serializer):
    symbol = serializers.CharField(max_length=10)
