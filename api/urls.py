from django.urls import path
from .views import ForexAnalysisView, SymbolAnalysisView

urlpatterns = [
    path('analyze/', ForexAnalysisView.as_view(), name='analyze'),
    path('analyze-symbol/', SymbolAnalysisView.as_view(), name='analyze_symbol'),

]

