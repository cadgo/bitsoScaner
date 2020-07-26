#!/usr/bin/env python3
import django, os, time
from plugins import sc_plugins
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangobitso.settings')
django.setup()
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from bitsoScaner import models
import sys, logging, threading 
import bitso, threading, queue

class Scanner():
    """
        El scanner lo que busca es interactuar con django y con su base de datos
        el scanner es quien lleva el logging

        mail - mail de la cuenta de bitso
    """
    version="xxx"
    description = "xxx"
    def __init__(self,mail, logfile="bitso.log"):
        self.api=None
        self.bitsoMail = mail
        logging.basicConfig(filename=logfile, format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")
        if not self._isValidaAccount(mail):
            logging.error("La cuenta provista no existe %s", mail)
            sys.exit()


    def _isValidaAccount(self,mail):
        """
        return true si existe en la base de datos
        """
        try:
            ac = models.BitsoAcount.objects.get(bitsomail=mail)
        except ObjectDoesNotExist:
            return False
        return True
    
    def GetBitsoKeyPass(self):
        """
            regresa los datos de la cuenta o false si la cuenta esta bacia
        """
        d = models.BitsoAcount.objects.get(bitsomail=self.bitsoMail)
        if len(d.bitsokey) == 0 or len(d.bitsosecret) == 0:
            return False, False
        return d.bitsokey, d.bitsosecret


    def BitsoLogin(self, key, password):
        """
            regresa la conexion a bitsomail o False si existe algun error.
        """
        try:
            cc = bitso.Api(key, password)
            cc.account_status()
        except bitso.errors.ApiError:
            return False
        return cc

    def SupportedBalances(self):
        """
            Rertun the list of supported coins or None si esta vacia
        """
        coins = []
        supCoins = models.BitsoBalance.SupportedBalances
        if len(supCoins) == 0:
            raise ValueError('There is not supported coins to continue')
        for x in supCoins:
            coins.append(x[0])
        return coins

    def RunBalancePlugin(self, coin_list):
        thread_loop = []
        QueueBalance=queue.Queue()
        for cc in coin_list:
            tr = sc_plugins.BalanceUpdater(api=self.api, desc=f"Balance para {cc}")
            thread_loop.append(tr)
            tr.PluginInitialize(cc, QueueBalance)
            tr.start()
        for cc in thread_loop:
            cc.join()
        if len(coin_list) != QueueBalance.qsize():
            raise AttributeError('La longitud de la lista de monedas {} difiere de las obtenidas del servidor'.format(len(coin_list)))
        return QueueBalance
    
    def InsertBalanceDB(self, coin, total):
        """
            actualiza la bd de datos de balance
            Si existe la moneda la actualizamos
            Si no existe la creamos

            return True si todo esta bien si no regresomos False
        """
        balanceNotFound=False
        bitsoAccount = models.BitsoAcount.objects.get(bitsomail=self.bitsoMail)
        if not coin in self.SupportedBalances():
            return False
        try:
            balance_base = models.BitsoBalance.objects.filter(BitsoAcount__bitsomail=self.bitsoMail).get(BalanceCoin=coin)
        except models.BitsoBalance.DoesNotExist:
            logging.debug("La moneda %s no existe en la BD", coin)
            balanceNotFound=True
        if balanceNotFound:
            #logging.info("Salvando el balance de %s en la BD con un total de %.6f", coin, total)
            s = models.BitsoBalance(BitsoAcount=bitsoAccount, BalanceUpdate=timezone.now(), BalanceCoin=coin, Balance=total)
            s.save()
            return total
        else:
            #logging.info("Actualizamos %s, con total %.6f", coin, total)
            q = models.BitsoBalance.objects.filter(BalanceCoin=coin).update(BalanceUpdate=timezone.now(), Balance=total)
            return  total
       
    def balance_Operationlogging(self, balances):
        if len(balances) <= 0:
            logging.error("Balance_Operation: No hay balances")
            return False
        for xx in balances:
            dict_val = queue_balance.get()
            popitem = dict_val.popitem()
            insert_result =Sc.InsertBalanceDB(popitem[0], popitem[1])
            if insert_result is False:
                logging.error("No se pudo insertar el balance de la moneda %s", popitem[0])
            else:
                logging.info("Salvando el balance de %s en la BD con un total de %.6f", popitem[0], insert_result)
    
    def OperationSellItter(self):
        models_sell = models.OperationSellTo.objects.filter(Account__bitsomail=self.bitsoMail)
        if len(models_sell) == 0:
            yield False
        for mds in models_sell:
            yield mds
    
    def LoggingSeparator(self, message, prf='='):
        pads = prf*15
        logging.info("%s [%s] %s", pads, message, pads)

    def LoggingStandartOps(self, exc_sell_ops, exc_buy_ops):
        """
            cuando una operacion no cae en venta o compra se loggea en esta sección
        """
        if not isinstance(exc_sell_ops, list) or not isinstance(exc_sell_ops, list):
            return False
        standard_ops_sell=models.OperationSellTo.objects.exclude(pk__in=exc_sell_ops)
        standard_ops_buy=models.OperationBuy.objects.exclude(pk__in=exc_buy_ops)
        self.LoggingSeparator("OPERACIONES")
        for sos in standard_ops_sell:
            message = f"{sos.DigitalCoin} {sos.Balance} [Adquirido {sos.ValorCompra}]"
            logging.info("%s",message)
        

    def LoggingSellOps(self, Queue_sell):
        """
            cuando una operacion es de venta se loggea aqui
        """
        pass

    def LoggingBuyOps(self, Queue_buy):
        """
            cuando un operacion de compra es procesada se loggea aqui
        """
        pass

    def ListOfValidSellOperations(self):
        valid_operations = queue.Queue()
        no_sell_operations = queue.Queue()
        threads = []
        for e_op in self.OperationSellItter():
            if e_op is False:
                return False
            t=sc_plugins.PluginQuoteStandardandSell(api=Sc.api, pk=e_op.pk, balance=e_op.Balance, value_expected=e_op.ValorExpected, digital_coin=e_op.DigitalCoin)
            t.PluginInitialize(valid_operations, no_sell_operations)
            threads.append(t)
            t.start()
        for tjoin in threads: tjoin.join()
        return valid_operations
    
    def ListofOperations(self, queue):
        queue_size = queue.qsize()
        list_queue = []
        if queue_size < 0:
            return False
        for i in range(queue.qsize()):
            list_queue.append(queue.get())
        return list_queue

if __name__ == '__main__':
    if len(sys.argv) < 1:
        print("Se requiere una cuenta valida para continuar")
        sys.exit()
    Sc=Scanner(sys.argv[1])
    key, password = Sc.GetBitsoKeyPass()
    ca = Sc.BitsoLogin(key, password)
    if not ca: 
        logging.error("No fue posible loggearse a bitso con las credenciales")
    else:
        Sc.api = ca
    balances = Sc.SupportedBalances()
    queue_balance= Sc.RunBalancePlugin(balances)
    Sc.balance_Operationlogging(balances)
    queue_sell_op_id = Sc.ListOfValidSellOperations()
    list_ops_sells=Sc.ListofOperations(queue_sell_op_id)
    Sc.LoggingStandartOps(list_ops_sells, [])
