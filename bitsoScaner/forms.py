from django import forms
from .models import BitsoAcount
from django.forms import formset_factory

class BitsoAccountForms(forms.ModelForm):
    bitsosecret = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = BitsoAcount

        fields = ['bitsomail', 'bitsokey', 'bitsosecret']


class CoinCalc(forms.Form):
	Max_Value=forms.FloatField(required=True, max_value=100_000_000, min_value=0)
	Min_Value=forms.FloatField(required=True, max_value=100_000_000, min_value=0)
	Monto=forms.FloatField(required=True, max_value=100_000_000, min_value=0)


CoinCalcFormSet=formset_factory(CoinCalc, min_num=1, extra=2, max_num=3)