from django.db import models

class ForexSymbol(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return self.name

class Trade(models.Model):
    symbol = models.ForeignKey(ForexSymbol, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    order_type = models.CharField(max_length=4)  # 'BUY' or 'SELL'
    volume = models.FloatField()
    sl_price = models.FloatField()
    tp_price = models.FloatField()
    order_number = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.symbol.name} - {self.order_type} - {self.timestamp}"

class SymbolAnalysis(models.Model):
    symbol = models.ForeignKey(ForexSymbol, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    kvo = models.FloatField(null=True, blank=True)
    signal = models.FloatField(null=True, blank=True)
    hist = models.FloatField(null=True, blank=True)
    sl_price = models.FloatField(null=True, blank=True)
    tp_price = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.symbol.name} - {self.timestamp}"

