from django.db import models
from django.utils import timezone
# Create your models here.

class  OperationAction(models.Model):
    SupportedCoins = (('btc', 'btc'), ('eth', 'eth'), ('ltc','ltc'),("tusd", "tusd"))
    Description = models.CharField(max_length=250, default='No description')
    Balance = models.FloatField(default=0)
    #Actions = models.FloatField(default=0)
    ValorExpected = models.FloatField(default=0)
    DigitalCoin = models.CharField(max_length=10, choices=SupportedCoins, default='btc')
    SendMail = models.BooleanField(default=True)

class BitsoAcount(models.Model):
    #BistoAcID = models.ForeignKey(BitsoDataConfig, on_delete=models.CASCADE)
    #BistoBalanceID = models.ForeignKey(BitsoBalance, on_delete=models.CASCADE)
    bitsomail = models.EmailField(max_length=100)
    bitsokey = models.CharField(max_length=30)
    bitsosecret = models.CharField(max_length=100)

class OperationSellTo(OperationAction):
    Account = models.ForeignKey(BitsoAcount, on_delete=models.CASCADE)
    BuyDate = models.DateField(default=timezone.now)
    BuyHour = models.TimeField(auto_now=False)
    ValorCompra = models.FloatField(default=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class OperationBuy(OperationAction):
    Account = models.ForeignKey(BitsoAcount, on_delete=models.CASCADE)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class BitsoBalance(models.Model):
    BitsoAcount = models.ForeignKey(BitsoAcount, on_delete=models.CASCADE)
    SupportedBalances = (('btc', 'btc'), ('eth', 'eth'), ('ltc', 'ltc'),('mxn', 'mxn'),("tusd", "tusd"))
    #BitsoAcount = models.OneToOneField(BitsoAcount, on_delete=models.CASCADE, primary_key=True)
    BalanceUpdate = models.DateField(default=timezone.now)
    BalanceCoin = models.CharField(max_length=10, choices=SupportedBalances, default='btc')
    Balance = models.FloatField(default=0)

class BitsoDataConfig(models.Model):
    BitsoAcount = models.OneToOneField(BitsoAcount, on_delete=models.CASCADE, primary_key=True)
    ConfigName=models.CharField(max_length=100)
    bitsoScanerRefresh = models.DecimalField(max_digits=2, decimal_places=0)
    #MailReceivers = models.EmailField(max_length=100)
    #MailAccountID = models.ForeignKey(SenderMailAccount, on_delete=models.CASCADE)

class SenderMailAccount(models.Model):
    MailAccount = models.EmailField(max_length=100)
    MailKey = models.CharField(max_length=100)
    BitsoAcount = models.OneToOneField(BitsoAcount, on_delete=models.CASCADE, primary_key=True)
    MailReceivers = models.EmailField(max_length=100)
