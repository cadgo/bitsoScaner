from django.shortcuts import render
from django.http import HttpResponse
from django.views import generic
from django.views.generic.edit import FormView
from . import forms, models

# Create your views here.
def index(request):
    return HttpResponse("Estamos en Index")

class CoinDashboard(FormView):
	template_name = "bitsoScaner/coin_dashboard.html"
	form_class=forms.CoinCalcFormSet

	def get(self,request, acc, coin, *args, **kargs):
		#print(f"account {acc}, moneda {coin}")
		ini=[]
		qcoin=models.BitsoTicker.objects.filter(bookname=coin).last()
		quotes=models.BitsoDataConfig.objects.filter(pk=acc).last()
		if qcoin is None:
			return render(request, self.template_name, {"error":f"{coin} not found"})
		if quotes.quote1 == 0 or quotes.quote2 == 0 or quotes.quote3==0:
			return render(request, self.template_name, {"error":f"Quotes with cero value"})
		ini=[{'Max_Value': qcoin.high, 'Min_Value': qcoin.low, 'Monto': quotes.quote1},
			 {'Max_Value': qcoin.high, 'Min_Value': qcoin.low, 'Monto': quotes.quote2},
			 {'Max_Value': qcoin.high, 'Min_Value': qcoin.low, 'Monto': quotes.quote3}]
		return render(request, self.template_name, {"forms":self.form_class(initial=ini), "coin": coin})
		#return render(request, self.template_name)