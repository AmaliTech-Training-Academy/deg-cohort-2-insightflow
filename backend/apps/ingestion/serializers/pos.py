from rest_framework import serializers

from ..models.pos import PosTransaction, PosTransactionLine


class PosTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PosTransaction
        fields = [
            'posTransactionId',
            'storeId',
            'cashierId',
            'transactionDatetime',
        ]


class PosTransactionLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PosTransactionLine
        fields = [
            'lineId',
            'posTransactionId',
            'productSKU',
            'quantity',
            'unitPrice',
            'discountApplied',
            'totalAmount',
        ]
