from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.views import generic, View
from django.views.generic.edit import FormView
from . import forms, models

# Create your views here.
def index(request):
    return HttpResponse("Estamos en Index")

class CoinCalc(FormView):
    """
        CoinCalc nos debe dar de todas las monedas la mejor inversion a hacer
        CoinDashboard nos da lo mismo pero nosotros lo pedimos, CoinCalc cuando se pida va a hacer un lookup a todas las monedas y nos dira cual tiene mejor
        ganacias
    """
    template_name = "bitsoScaner/boption.html"
    form_class= forms.CoinReqCalc

    def get(self, request, acc):
        return render(request, self.template_name, {'form': self.form_class(), 'acc': acc})
    

    def post(self, request, acc):
        maxval=0
        icoin=""
        sc = models.OperationAction.SupportedCoins
        form = self.form_class(request.POST)
        if form.is_valid():
            postdata = form.cleaned_data
            value = postdata['Value']
            if value < 1000:
                return render(request, self.template_name, {'error': True, 'merror': "No es posible procesar un valor menor a 1000"})
            for j in sc:
                lastdbvalue=models.BitsoTicker.objects.filter(bookname=j[0]).latest('datetime')
                pbuyc=value/lastdbvalue.low
                rbuyc=round(pbuyc*lastdbvalue.high,2)
                if maxval < rbuyc:
                    maxval = rbuyc
                    icoin = j[0]
                print(f"la moneda {j[0]}, tiene un val {rbuyc} max {lastdbvalue.last} low {lastdbvalue.low}")
            print(f"la mejor opcion de moneda es {icoin}")
            return render(request, self.template_name,{'form': self.form_class(), 'acc': acc, 'bc': icoin, 'calcv': maxval})
        else:
            return Http404('Invalid Form')


class CoinDashboard(FormView): 
    template_name = "bitsoScaner/coin_dashboard.html" 
    form_class=forms.CoinCalcFormSet

    def get(self,request, acc, coin, *args, **kargs):
	#print(f"account {acc}, moneda {coin}")
        ini=[]
        #qcoin=models.BitsoTicker.objects.filter(bookname=coin).last()
        qcoin=models.BitsoTicker.objects.filter(bookname=coin).latest('datetime')
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
