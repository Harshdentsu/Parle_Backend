from django.urls import path
from .views import ConfirmOrderView, ParleProduct
urlpatterns = [
    path('chat/', ParleProduct.as_view()),
    path('confirmorder/', ConfirmOrderView.as_view()),
]
