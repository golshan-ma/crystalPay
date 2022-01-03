from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from .models import Gateway, Configuration
from django.views.decorators.csrf import csrf_exempt


# Create your views here.


@csrf_exempt
def create_gateway(request):
    if request.POST.get('config') and request.POST.get('address') and request.POST.get('metadata') and request.POST.get(
            'amount') and request.POST.get('signature') and \
            request.POST.get('callback'):
        config_obj = get_object_or_404(Configuration, slug=request.POST.get('config'))
        new_gateway = Gateway(
            config=config_obj,
            creator_address=request.POST.get('address'),
            metadata=request.POST.get('metadata'),
            amount=request.POST.get('amount'),
            signature=request.POST.get('signature'),
            callback_url=request.POST.get('callback')
        )
        new_gateway.save()
        return JsonResponse({'result': new_gateway.slug}, status=200)
    else:
        return JsonResponse({'result': 'bad request'}, status=400)


def pay_view(request, slug):
    gateway = get_object_or_404(Gateway, slug=slug)
    if gateway.is_paid or gateway.is_refunded:
        return HttpResponse('gateway is done')
    gateway.check_validity()
    if gateway.is_expired:
        return HttpResponse('gateway is expired')
    errors = request.GET.get('error')
    context = {
        'gateway': gateway,
        'error': errors,
    }
    return render(request, template_name='payments/pay.html', context=context)


def confirm_payment(request, slug):
    gateway = get_object_or_404(Gateway, slug=slug)
    if not gateway.is_paid or not gateway.is_refunded or not gateway.is_expired:
        if request.method == 'POST' and request.POST.get('refund_address'):
            if len(request.POST.get('refund_address')) < 32:
                n_url = "%s?error=1" % reverse('pay-url', args=[gateway.slug])
                return redirect(n_url)
            gateway.refund_address = request.POST.get('refund_address')
            gateway.save()
            gateway.execute_transaction()
            if gateway.is_paid:
                url = reverse('final-payment-url', args=[gateway.slug])
                return redirect(url)
            else:
                url = reverse('check-payment-url', args=[gateway.slug])
                return redirect(url)


def final_view(request, slug):
    gateway = get_object_or_404(Gateway, slug=slug)
    if gateway.is_paid:
        receipt = gateway.sign_receipt()
        msg = receipt['message']
        sign = receipt['signature']
        context = {'Gateway': gateway, 'massage': msg, 'sign': sign}
        return render(request, template_name='payments/final.html', context=context)
    else:
        url = reverse('check-payment-url', args=[gateway.slug])
        return redirect(url)


def check_payment(request, slug):
    gateway = get_object_or_404(Gateway, slug=slug)
    if not gateway.is_paid and gateway.is_refunded:
        gateway.check_validity()
    receipt = gateway.sign_receipt()
    msg = receipt['message']
    sign = receipt['signature']
    return JsonResponse({"massage": msg, 'sign': sign}, status=200)


def paid_amount(request):
    # request should be ajax and method should be GET.
    if request.method == "GET":
        # get the nick name from the client side.
        slug = request.GET.get("slug", None)
        # check for the nick name in the database.
        if Gateway.objects.filter(slug=slug).exists():
            n = Gateway.objects.get(slug=slug)
            n.update_paid_amount()

            return JsonResponse({"result": n.paid_amount, 'percent': n.width_percent()}, status=200)
        else:
            return JsonResponse({"result": False}, status=400)

    return JsonResponse({}, status=400)
