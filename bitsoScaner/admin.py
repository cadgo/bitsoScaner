from django.contrib import admin
from .models import *
from django import forms
# Register your models here.

@admin.register(OperationSellTo)
class AdminOperationSell(admin.ModelAdmin):
    list_display = ('BuyDate','BuyHour','DigitalCoin', 'Balance', 'ValorCompra','ValorExpected', 'Description')
    fieldsets=(
        (None,{'fields': ('Account',)}),
        ('Operation Time', {'fields': ('BuyDate', 'BuyHour')}),
        ('Currency Info', {'fields': ('DigitalCoin', 'Balance', 'ValorExpected', 'ValorCompra')}),
        ('Acciones', {'fields': ('Description','SendMail', 'SlackHook')}),
    )
@admin.register(OperationBuy)
class AdminOperationBuy(admin.ModelAdmin):
    list_display=('DigitalCoin', 'ValorExpected', 'Description')
    fieldsets=(
        ('Info de Cuenta',{'fields': ("Account",)}),
        ('Info de Compra', {'fields': ("DigitalCoin","ValorExpected", "Balance")}),
        ("Acciones", {"fields": ('Description', 'SendMail', 'SlackHook')}),
    )

@admin.register(BitsoBalance)
class AdminBitsoBalance(admin.ModelAdmin):
    list_display=('BalanceUpdate', 'Balance', 'BalanceCoin')

class BitsoAcountForm(forms.ModelForm):
    bitsosecret = forms.CharField(widget=forms.PasswordInput)

class BistoSecretAdmin(admin.ModelAdmin):
    form = BitsoAcountForm
    list_display= ('bitsomail', 'bitsokey')
    fieldset = ('bitsomail', 'bitsokey', 'bitsosecret')

#admin.site.register(OperationBuy)
#admin.site.register(BitsoAcount)
admin.site.register(BitsoAcount, BistoSecretAdmin)
admin.site.register(BitsoDataConfig)
admin.site.register(SenderMailAccount)
admin.site.register(SlackWebHook)
#admin.site.register(BitsoBalance)
#admin.site.register(OperationSellTo)