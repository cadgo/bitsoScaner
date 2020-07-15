#!/usr/bin/env python3
import threading, time, queue  
import bitso
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

    def __str__(self):
        return f"{self.PluginName}: {self.PlugIndescription}"
    
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
