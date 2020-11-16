#!/usr/bin/env python3
import threading, time, queue  
import bitso, decimal
import sys, re
sys.path.insert(1, '/home/carlos_diaz_s3c/python/cdtool')
from SrvPost import slackWebHookPost
from cdmail import SendMailAlertGmail
class plugin():
    """
        clase que nos ayudara con el tema del multithread, todo lo que herede de aqui debe trabajar como un plug in independiente corriendo como hilo
        y solo realizando ciertas tareas muy especificas

        plugin de alarmas
        plugin de ventas
        plugin de compras
    """
    def __init__(self, **kwargs):
        self.PluginName = type(self).__name__
        self.PlugIndescription = kwargs.get('desc')
        self._Initialized = False

    def PluginInitialize(self):
        if not self._Initialized:
            raise RuntimeError("Plugin not initialized")

    def __str__(self):
        return f"{self.PluginName}: Pluin Class Handler"
    
    def run(self):
        if not self._Initialized:
            raise RuntimeError("Can't run without initilization")

class BitsoApiPlugin(plugin):
    def __init__(self, **kwargs):
        self.BitConn = kwargs.get('api')
        if not isinstance(self.BitConn, bitso.Api):
            raise ValueError('ap parameter is not a bitsoApi instance')
        self.ComQueue=None
        super().__init__(**kwargs)
     
    def __str__(self):
        return f"{self.PluginName}: {self.PlugIndescription}"

class BalanceUpdater(BitsoApiPlugin, threading.Thread):
    """
        BalanceUpdater, Demonio que corre en el background y cada cierto tiempo actualiza la base de datos del Balance
        PluginDescription: Plugin que corre en background y actualiza en la BD de datos los balances
        requiere:
        self.api: la conexion a la api
        self.SupportedCoins: Las monedas por las que preguntara
        self.Mail: El mail de la cuenta donde insertara estos datos

        Los pasamos con self.Initialize
    """
    def __init__(self, **kwargs):
        self._Initialized=False
        self.SupportedCoins = None
        super().__init__(**kwargs)
        threading.Thread.__init__(self)
        
    def PluginInitialize(self, coin,  lqueue):
        self.coin_ask = coin
        if isinstance(lqueue, queue.Queue):
            self.ComQueue = lqueue
        else:
            raise ValueError("No hay un Queue Valido")
        if len(self.coin_ask) == 0:
            raise ValueError("No hay monedas para inspeccionar")
        self._Initialized = True
        super().PluginInitialize()
        return True

    def run(self):
        """
            Corre como demonio actaulizando los balances en la BalanceDeamon
        """
        super().run()
        RetBalance = {self.coin_ask:0}
        bal = self.BitConn.balances()
        #if len(self.SupportedCoins) == 0 or self.UsedMail==None:
        #raise ValueError("Establece el valor de self.SupportedCoins y self.UsedMail")
        xbalance = getattr(bal, self.coin_ask)
        RetBalance[self.coin_ask] = getattr(xbalance, 'total')
        self.ComQueue.put(RetBalance)

class PluginQuoteStandardandSell(BitsoApiPlugin, threading.Thread):
    """
        Genera las cotizaciones para ver si la operacion de venta es posible o no
        recibe el pk, el balancce, valor esperado
        para saber si es necesario vender
    """
    def __init__(self, **kwargs):
        self.pk = kwargs['pk'] if kwargs['pk'] > 0 else 0 
        self.Balance = kwargs['balance'] if kwargs['balance'] >0 else 0
        self.ValueExpected = kwargs['value_expected'] if kwargs['value_expected'] >0 else 0
        self.DigitalCoin = kwargs['digital_coin']
        if len(self.DigitalCoin) == 0:
            raise ValueError("Digital Coin can't be empty")
        if self.pk == 0 or self.Balance == 0 or self.ValueExpected==0:
            raise ValueError('Error parsing one of the values')
        self._Initialized = False
        super().__init__(**kwargs)
        threading.Thread.__init__(self)

    def PluginInitialize(self, valid_sell_queue, no_sell_queue):
        if isinstance(valid_sell_queue, queue.Queue) or isinstance(no_sell_queue, queue.Queue):
            self.queue_valid_sell_pks = valid_sell_queue
            self.queue_no_sell_pks = no_sell_queue
        else:
            raise ValueError("No hay un Queue Valido")
        self._Initialized = True
        super().PluginInitialize()
        return True

    def run(self):
        super().run()
        retdic = {'pk':None, 'quoted_value':None}
        book = self.DigitalCoin+'_mxn'
        decimal.getcontext().prec=8
        balance=decimal.Decimal(self.Balance)
        ticker = self.BitConn.ticker(book)
        bitso_fees = self.BitConn.fees()
        fees = getattr(bitso_fees,book).fee_percent / 100        
        #price = balance - getattr(bitso_fees.withdrawal_fees, self.DigitalCoin)
        price = (balance * ticker.last) - fees 
        if price >= self.ValueExpected:
            retdic['pk']= self.pk; retdic['quoted_value']=price
            self.queue_valid_sell_pks.put(retdic)
        else:
            retdic['pk']= self.pk; retdic['quoted_value']=price
            self.queue_no_sell_pks.put(retdic)

class PluginQuoteBuy(BitsoApiPlugin, threading.Thread):
    """
        Genera las cotizaciones para ver si la operacion de compra es posible o no
        recibe el pk, el balancce, valor esperado
        para saber si es necesario comprar
    """
    def  __init__(self, **kwargs):
        self.pk = kwargs['pk'] if kwargs['pk'] > 0 else 0 
        self.ValueExpected = kwargs['value_expected'] if kwargs['value_expected'] >0 else 0
        if self.pk == 0 or self.ValueExpected==0:
            raise ValueError('Error parsing one of the values')
        self.DigitalCoin = kwargs['digital_coin']
        if len(self.DigitalCoin) == 0:
            raise ValueError("Digital Coin can't be empty")
        self._Initialized = False
        super().__init__(**kwargs)
        threading.Thread.__init__(self)

    def PluginInitialize(self, valid_buy_queue, remaining_buy_queue):
        if isinstance(valid_buy_queue, queue.Queue) or isinstance(remaining_buy_queue, queue.Queue):
            self.queue_valid_buy_pks = valid_buy_queue
            self.queue_remaining_buy_pks = remaining_buy_queue
        else:
            raise ValueError("No hay un Queue Valido")
        self._Initialized = True
        super().PluginInitialize()
        return True

    def run(self):
        super().run()
        retdic= {'pk':None, 'quoted_value':None}
        book=self.DigitalCoin+'_mxn'
        last_coin_value = decimal.Decimal(self.BitConn.ticker(book).last)
        retdic['pk']= self.pk; retdic['quoted_value']=last_coin_value
        if self.ValueExpected  >= last_coin_value:
            self.queue_valid_buy_pks.put(retdic)
        else:
            self.queue_remaining_buy_pks.put(retdic)

class PluginAlarms(plugin):
    def __init__(self, reference_data, **kwargs):
        self.message = ""
        self.reference= reference_data
        super().__init__(**kwargs)

    def AppendMessage(self, amessage):
        if len(amessage) > 0:
            self.message = self.message+amessage
            self.message = self.message+'\n'
            return True
        else:
            False

class PluginSlackAlarm(PluginAlarms, threading.Thread):
    def __init__(self, reference_data="",  **kwargs):
        super().__init__(reference_data, **kwargs)
        threading.Thread.__init__(self)
    
    def PluginInitialize(self, webhook):
        hook_regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        if len(webhook) > 0 or re.match(hook_regex, webhook) != None:
            self.webhook = webhook
            self._Initialized = True
            super().PluginInitialize()
        else: 
            self._Initialized = False
            raise ValueError("webhook parameter error")

    def run(self):
        super().run()
        prog_message = self.reference + '\n' + self.message
        slackWebHookPost(self.webhook, prog_message)


class PluginMailAlarm(PluginAlarms, threading.Thread):
    def __init__(self, reference_data, **kwargs):
        super().__init__(reference_data, **kwargs)
        threading.Thread.__init__(self)

    def __StringNotEmtpy(self,value):
        if len(value) <= 0:
            return False
        else:
            return True
    
    def __ValidEmail(self, mail):
        mail_regex="^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$"
        if re.match(mail_regex, mail) != None:
            return True
        else:
            return False

    def PluginInitialize(self,**kwargs): 
        self.sender = kwargs['sender'] if self.__StringNotEmtpy(kwargs['sender']) else False
        self.receivers = kwargs['receivers'] if self.__StringNotEmtpy(kwargs['receivers']) else False
        self.sender_password = kwargs['sender_password'] if self.__StringNotEmtpy(kwargs['sender_password']) else False
        self.subject = kwargs['subject'] if self.__StringNotEmtpy(kwargs['subject']) else False
        print(self.sender)
        if not self.__ValidEmail(self.sender):
            raise ValueError("Invalid Mail Value")
        print(self.receivers)
        if not self.__ValidEmail(self.receivers):
            pass
            #raise ValueError("Invalid Receivers Value")
        if self.sender or self.receivers or self.sender_password or self.subject or self.mail_body:
            self._Initialized = True
            super().PluginInitialize()
        else:
            self._Initialized = False


    def run(self):
        super().run()
        SendMailAlertGmail(self.sender, self.receivers, self.sender_password, self.subject,self.message)


class AutoSell_Plugin(plugin, threading.Thread):
    def __init__(self, OID, **kwargs):
        self.OID = OID
        self.InitalTime = time.time()
        self.sleepTime = 5
        #El plugin checa cada 5 segundos la Operacion
        super().__init__(**kwargs)

    def PluginInitializ(self, **kwargs):
        t= kwargs['timer']
        if t > 0 and t < 10:
            t = t * 60
            self.exec_timer = t
            self._Initialized = True
            self.ExtraTime = t
            super().PluginInitialize()
        else:
            self._Initialized= False

    def run(self):
        end_time = self.InitalTime + self.ExtraTime
        r_time = self.InitalTime
        while r_time < end_time:
            print(f"Aun no se acaba la ejecucion del hilo con OID {self.OID}")
            time.sleep(self.sleepTime)
        else:
            print(f"Ha finalizado la ejecucion del hilo con OID {self.OID}, despues de {self.ExtraTime}")
            return
