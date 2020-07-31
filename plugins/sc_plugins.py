#!/usr/bin/env python3
import threading, time, queue  
import bitso, decimal
class plugin():
         """
             clase que nos ayudara con el tema del multithread, todo lo que herede de aqui debe trabanar como un plug in independiente corriendo como hilo
             y solo realizando ciertas tareas muy especificas
     
             plugin de logs
             plugin de alarmas
             plugin de ventas
             plugin de compras
         """
         plist = [] 
         def __init__(self, **kwargs):
             self.PluginName = type(self).__name__ 
             self.PlugIndescription = kwargs.get('desc')
             self._Initialized = False
         
         def PluginInitialize(self):
             if not self._Initialized:
                 raise RuntimeError("Plugin not initialized")
             plugin.plist.append(self)
         
         def __str__(self):
            return f"{self.PluginName}: Pluin Class Handler"

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
        self.pk = kwargs['pk'] if kwargs['pk'] > 0 else 1   
        self.ValueExpected = kwargs['value_expected'] if kwargs['value_expected'] >0 else 0
        if self.pk == 0 or self.ValueExpected==0:
            raise ValueError('Error parsing one of the values')
        self.DigitalCoin = kwargs['digital_coin']
        if len(self.DigitalCoin) == 0:
            raise ValueError("Digital Coin can't be empty")
        self._Initialized = False
        super().__init__(**kwargs)
        threading.Thread.__init__(self)

    def PluginInitialize(self, valid_buy_queue):
        if isinstance(valid_buy_queue, queue.Queue):
            self.queue_valid_buy_pks = valid_buy_queue
        else:
            raise ValueError("No hay un Queue Valido")
        self._Initialized = True
        super().PluginInitialize()
        return True

    def run(self):
        retdic= {'pk':None, 'quoted_value':None}
        book=self.DigitalCoin+'_mxn'
        last_coin_value = decimal.Decimal(self.BitConn.ticker(book).last)
        if self.ValueExpected  >= last_coin_value:
            retdic['pk']= self.pk; retdic['quoted_value']=last_coin_value
            self.queue_valid_buy_pks.put(retdic)
