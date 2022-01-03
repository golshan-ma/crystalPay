from django.urls import path
from . import views

urlpatterns = [
    path('create', views.create_gateway,
         name='create-url'),
    path('pay/<slug:slug>', views.pay_view, name='pay-url'),
    path('confirm/<slug:slug>',views.confirm_payment, name='confirm-payment-url'),
    path('paid-balance', views.paid_amount, name='get-paid-amount'),
    path('check/<slug:slug>', views.check_payment, name='check-payment-url'),
    path('final/<slug:slug>',views.final_view,name='final-payment-url')
]
