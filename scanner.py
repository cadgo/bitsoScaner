import os, sys
import django
import decimal, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangobitso.settings')
django.setup()
sys.path.insert(1, '/home/carlos_diaz_s3c/python/cdtool')
from cdmail import SendMailAlertGmail 
from SrvPost import slackWebHookPost
import sys, logging
from django.utils import timezone
#Any import from models, views, etc
from bitsoScaner import models
import bitso as bt
from bitso.errors import ApiClientError, ApiError

class Scanner(object):
    """Bitso Scaner para buscar actualizaciones en la pagina de bitso y de esta manera tomar descisiones de compra"""
    Version = 1

    def __init__(self, bitsoMail, logfile="bitso.log"):
        self.BitsoAPI = None
        self.queryinfo = models.BitsoAcount.objects.filter(bitsomail=bitsoMail)
        assert len(self.queryinfo)!=0, "Error Account {} could not be found in the database".format(bitsoMail)
        assert len(self.queryinfo)<2, "Solo se puede tener una misma cuenta con el mismo correo; cuentas: {}".format(len(self.queryinfo))
        self.logfile = logfile
        self.AccMail = self.queryinfo[0].bitsomail
        self.SecsToSleep=30
        self.ErrorMaxCounter=3
        self.ErrorsOcurred=1

        self.__logfileConfiguration()

    def BitsoConnect(self):
        try:
            self.BitsoAPI = bt.Api(self.queryinfo[0].bitsokey, self.queryinfo[0].bitsosecret)
        except ApiClientError:
            logging.error("No es posible contactar a la api de bits, saliendo del programa")
            sys.exit(-1)
        logging.info("connecting with the API")

    def __logfileConfiguration(self):
        logging.Formatter.converter = time.localtime
        logging.basicConfig(filename=self.logfile, format='%(asctime)s - %(levelname)s - %(message)s',
                            level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
        logger = logging.getLogger(__name__)

    def __str__(self):
        return "BitSoCaner v{} using account".format(Scanner.Version, self.AccMail)

    def __balanceConverter(self, coinname, total):
        if coinname == 'mxn':
            logging.info('%s con balance: %d', coinname, total)
            return int(total)
        else:
            logging.info('%s con balance: %.6f', coinname, total)
            return float(total)

    def UpdateBitsoBalande(self):
        """Verificar si existe un balance si no existe hay que pedirlo de bitso y si ya existe hay q actualizarlo"""
        suportedCoins = models.BitsoBalance.SupportedBalances
        balance = models.BitsoBalance.objects.filter(BitsoAcount__bitsomail=self.AccMail)
        nb = self.BitsoAPI.balances()
        qi = models.BitsoAcount.objects.filter(bitsomail=self.AccMail).get()
        if len(balance) == 0:
            logging.info("No existe balance, actualizando")
            #print(suportedCoins)
            #Si ya existe un balance lo borramos de las tablas y los actualizamos si no solo actualizamos
            for x in range(len(suportedCoins)):
                xbalance = getattr(nb, suportedCoins[x][0])
                name = getattr(xbalance, 'name')
                total = getattr(xbalance, 'total')
                total = self.__balanceConverter(name, total)
                if total != 0:
                    logging.info("salvando el balance de %s en la BD con un total %.6f", name, total)
                    s = models.BitsoBalance(BitsoAcount=qi, BalanceUpdate=timezone.now(), BalanceCoin=name, Balance=total)
                    s.save()
        else:
            logging.info("Removiendo balances anteriores")
            for bal in balance:
                logging.info("Removiendo balance %s", bal.BalanceCoin)
                bal.delete()
            logging.info("Agregando nuevos balances")
            for x in range(len(suportedCoins)):
                xbalance = getattr(nb, suportedCoins[x][0])
                name = getattr(xbalance, 'name')
                total = getattr(xbalance, 'total')
                total = self.__balanceConverter(name, total)
                #print("balance", name, "con un total ", total)
                if total != 0:
                    logging.info("salvando el balance de %s en la BD", name)
                    s = models.BitsoBalance(BitsoAcount=qi, BalanceUpdate=timezone.now(), BalanceCoin=name, Balance=total)
                    s.save()

    def GetConfigScanerRefresh(self):
        a=models.BitsoDataConfig.objects.filter(BitsoAcount__bitsomail=self.AccMail).first()
        return int(a.bitsoScanerRefresh)

    def GetOperationSell(self):
        return models.OperationSellTo.objects.filter(Account__bitsomail=self.AccMail)

    def GetOperationBuy(self):
        return models.OperationBuy.objects.filter(Account__bitsomail=self.AccMail)

    def GetBisto_fee_ticker_data(self, coin):
        """
			self.BitsoAPI.ticker meterlo a la BD
        """
        book=coin+'_mxn'
        one_coin_to_mxn='one_'+coin+'_to_mxn'
        withdrawal=coin+'_withdrawal_f'
        tickerdatabase=None
        rr = {}
        try:
            rr.update({coin:{'one_coin_to_mxn': '', withdrawal: '', 'bitso_percent_fee':'', }})
            ticker=self.BitsoAPI.ticker(book)
            tickerdatabase=models.BitsoTicker.objects.create(
                bookname=coin,
                ask=ticker.ask,
                bid=ticker.bid,
                high=ticker.high,
                last=ticker.last,
                low=ticker.low,
                datetime=ticker.created_at
                )
            tickerdatabase.save()
            lastvalue = ticker.bid
            rr[coin]['one_coin_to_mxn']=lastvalue
            feepercent=getattr(self.BitsoAPI.fees(), book).fee_percent
            rr[coin]['bitso_percent_fee'] = feepercent
            withdraw = getattr(self.BitsoAPI.fees().withdrawal_fees, coin)
            rr[coin][withdrawal] = withdraw
            logging.debug("recolectado fees y precios de bitso %s", rr)
        except: 
            logging.error("Error en la api para recopilar la información de %s", coin)
            time.sleep(self.SecsToSleep)
            self.ErrorsOcurred+=self.ErrorsOcurred
            logging.error("Se han encontrado %d Errores al recopiar los fees", self.ErrorsOcurred)
            if self.ErrorsOcurred > self.ErrorMaxCounter:
                raise ApiError
            self.GetBisto_fee_ticker_data(coin)
        return rr

    def QuoteToSell(self, quotedata, opsell):
        """
        Quotedata: el diccionario que contiene la cotizaciones tomadas de bitso
        opsell: tomado de la BD opsell es un elemento sobre el que vamos a generar la cotización
        Esta funcion procesa la moneda con quotedata y genera una cotización donde entrega el monto al momento de su ejecución
        para ver si es factible vender

        return: Deber regresar el valor de lo que cotiza nuestra moneda para compararlo con lo esperamos recibir
        Algo como  DONT SELL, gross 12221.97, value expected 18000.0
        """
        correctionvalue=200
        gross = 0
        opsellBalance=0
        decimal.getcontext().prec=8
        for t in range(len(quotedata)):
            if opsell.DigitalCoin in quotedata[t]:
                #logging.info("Generando Cotizacion para %s", opsell.DigitalCoin)
                opsellBalance = decimal.Decimal(opsell.Balance)
                #logging.info("El balance de %s es %.8f", opsell.DigitalCoin, opsellBalance)
                fee = quotedata[t][opsell.DigitalCoin]["bitso_percent_fee"]/ 100
                price = opsellBalance - quotedata[t][opsell.DigitalCoin][opsell.DigitalCoin+'_withdrawal_f']
                price = opsellBalance * quotedata[t][opsell.DigitalCoin]['one_coin_to_mxn']
                    #fee = price * fee
            # menos 100 para acercar a una cotizacion real
            #price = price - fee + correctionvalue
                return price
        return None

    def QuoteToBuy(self, quotedata, opbuy):
        """Regresa True para comprar y false para no comprar"""
        for t in range(len(quotedata)):
            if opbuy.DigitalCoin in quotedata[t]:
                if quotedata[t][opbuy.DigitalCoin]['one_coin_to_mxn'] < opbuy.ValorExpected:
                    #logging.info("Valor de compra Esperado de compra alcanzado")
                    return True, quotedata[t][opbuy.DigitalCoin]['one_coin_to_mxn']
                else:
                    #logging.info("Valor de compra no alcanzado")
                    return False, quotedata[t][opbuy.DigitalCoin]['one_coin_to_mxn']

    def SendMailWrapper(self, message, operation):
        """
            message: el mensaje
            Operation: vender o comprar
        """
        logging.info("sending email for opperation %s", operation)
        q=models.SenderMailAccount.objects.filter(BitsoAcount__bitsomail=self.AccMail).first()
        if q is None:
            return None
        sender=q.MailAccount
        password = q.MailKey
        Receivers= q.MailReceivers
        if not len(sender) and len(password) and len(Receivers):
            logging.error("Datos de las cuentas de correo incorrectas no data")
            return None
        subject = 'BitsoScaner Operacion ' + operation
        s = SendMailAlertGmail(sender, Receivers, password, subject, message)
        if s != False:
            return True

    def SendSlackMessage(self, message, operation):
        #q = models.SlackWebHook.objects.filter(BitsoAcount__bitsomail=self.AccMail)
        q = models.SlackWebHook.objects.filter(BitsoAcount__bitsomail="cadgo@hotmail.com")
        if q is None:
            return None
        for x in q:
            webmessage='BitsoScaner Operacion ' + operation + " " + message
            s=slackWebHookPost(x.hook, webmessage)
            if s[0] == True:
                logging.info('Enviendo mensaje slack para la cuenta %s', x.name)
                return True
            else:
                logging.wanrning('No se pudo contactar a Slack error %s', s[1])
                return False

    def MessagaSellOrBuy(self, op, no_value,*args):
        tt={
        'vender': lambda: "{} VENDER, valor para {} {} [Adqurido x {}]- [Cot en {}], valor esperado {}".format(no_value,args[0], args[1], args[2], args[3], args[4]),
        'comprar': lambda: "{} COMPRAR, {}: tiene un valor de {} esperamos {}".format(no_value,args[0], args[1], args[2]),
        }.get(op, lambda: None)()
        return tt

    def AlarmsGenerator(self, alarmpool):
        """
            Genera un buffer con todos los mensajes que seran enviados de un shoot y los envia a slack o al mail
        """
        #Gestor de envio de alarmas
        lenOpSell=len(alarmpool["opsell"])
        lenOpBuy=len(alarmpool["opbuy"])
        #Aqui se almacenan todos los mensajes que seran enviandos
        messagesell=messagebuy=""
        mailsell=slacksell=mailbuy=slackbuy=None
        if lenOpSell == 0 and lenOpBuy == 0:return False #Esta linea esta mals
        if lenOpSell > 0:
            for a in alarmpool["opsell"]:
                #choser={'SendMail': lambda: if a[0].SendMail: self.SendMailWrapper() , 'SlackHook': "slackfunc"}
                coin=a[0].DigitalCoin ; Balance=a[0].Balance
                quote=a[1] ; ValueExpected=a[0].ValorExpected
                #message="HORA DE VENDER, valor cotizado para {} {} - {}, valor esperado {}".format(coin, Balance, quote, ValueExpected)
                message=self.MessagaSellOrBuy('vender', "", coin ,Balance, a[0].ValorCompra,quote, ValueExpected)
                if a[0].SendMail or a[0].SlackHook:
                    messagesell+=message+"\n"
                if a[0].SendMail:
                    mailsell="sell-mail"
                if a[0].SlackHook:
                    slacksell="sell-slack"
                logging.info(message)
        else:
            logging.warning("No hay Alarmas de Ventas :(")
        if lenOpBuy > 0:
            for a in alarmpool["opbuy"]:
                coin=a[0].DigitalCoin; quote=a[1]
                ValueExpected=a[0].ValorExpected
                #message = "HORA DE COMPRAR, {}: tiene un valor de {} esperamos {}".format(coin, quote, ValueExpected)
                message=self.MessagaSellOrBuy("comprar", "", coin, quote, ValueExpected)
                if a[0].SendMail or a[0].SlackHook:
                    messagebuy+=message+"\n"
                if a[0].SendMail:
                    mailbuy="buy-mail"
                if a[0].SlackHook:
                    slackbuy="buy-slack"
                logging.info(message)
        else:
            logging.warning("No hay alarmas de compra :(")
        sw={"sell-mail": lambda: self.SendMailWrapper(messagesell, "vender"),
            "sell-slack": lambda: self.SendSlackMessage(messagesell, "vender"),
            "buy-mail": lambda: self.SendMailWrapper(messagebuy, "comprar"),
            "buy-slack": lambda: self.SendSlackMessage(messagebuy, "comprar")}
        cc=[mailsell,slacksell, mailbuy, slackbuy]
        #c=[b.get(a, lambda:None)() for a in ['mailsell', 'slacksell', 'mailbuy', 'slackbuy']]
        for c in cc:
            sw.get(c, lambda:None)()
        return True

    def Operations(self):
        """
            Regresa todas las operaciones de venta en una tupla de opsell y opbuy, en un conjunto
        """
        coins = models.OperationSellTo.SupportedCoins
        datasell = []
        opsell = self.GetOperationSell()
        opbuy = self.GetOperationBuy()
        logging.info("Tenemos %d operaciones de venta", len(opsell))
        logging.info("Recopilando información de precio de las cryptomonedas")
        messageinfo = {"opsell":[], "opbuy":[]}
        for x in coins:
            dd = self.GetBisto_fee_ticker_data(x[0])
            if dd != None:
                datasell.append(dd)
            else:
                time.sleep(30)
                self.Operations()
        if len(dd) == 0:
            logging.error("No se pudo recopilar el costo de las monedas %s", coins)
            raise Exception("No se pudo recopilar los costos de las monedas")
        #print(opsell)
        if opsell is not None:
            for ev in opsell:
                quote=self.QuoteToSell(datasell, ev)
                if ev.ValorExpected < quote:
                    messageinfo["opsell"].append([ev, quote])
                else:
                    #message="NO VENDER: valor cotizado para {} {} - {}, valor expected {}".format(ev.DigitalCoin, ev.Balance,quote, ev.ValorExpected)
                    message=self.MessagaSellOrBuy("vender", "NO", ev.DigitalCoin,ev.Balance,ev.ValorCompra, quote, ev.ValorExpected)
                    logging.info(message)
        if opbuy is not None:
            for ev in opbuy:
                ttb, val = self.QuoteToBuy(datasell, ev)
                if ttb:
                    messageinfo["opbuy"].append([ev, val])
                else:
                    #message="NO COMPRAR {}: tiene un valor de {}, esperamos {}".format(ev.DigitalCoin, val, ev.ValorExpected)
                    message=self.MessagaSellOrBuy("comprar", "NO", ev.DigitalCoin, val, ev.ValorExpected)
                    logging.info(message)
        #print(messageinfo)
        if len(messageinfo["opsell"]) ==0  and len(messageinfo["opbuy"]) == 0:
            print("No hay mensajes que evniar")
            messageinfo = {"opsell":[], "opbuy":[]}        
        return messageinfo

if __name__ == '__main__':
    if len(sys.argv) < 1:
        print("Se requiere una cuenta valida para continuar")
        sys.exit()
    Sc = Scanner(sys.argv[1])
    Sc.BitsoConnect()
    Sc.UpdateBitsoBalande()
    logging.info("entrando al loop principal")
    running=True
    while running:
        try:
            alarms=Sc.Operations()
            #print("Alarms", alarms)
            Sc.AlarmsGenerator(alarms)
            time.sleep(Sc.GetConfigScanerRefresh())
            #REMOVER PARA QUE FUNCIONE EN EL LOOP
            #running=False
        except KeyboardInterrupt:
            print("Saliendo de la aplicación")
            running=False
