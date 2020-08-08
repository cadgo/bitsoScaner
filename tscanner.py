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

    def GetConfigScanerRefresh(self):
        a=models.BitsoDataConfig.objects.filter(BitsoAcount__bitsomail=self.bitsoMail).first()
        return int(a.bitsoScanerRefresh)

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
    
    def OperationSellToItter(self):
        models_sell = models.OperationSellTo.objects.filter(Account__bitsomail=self.bitsoMail)
        if len(models_sell) == 0:
            yield False
        for mds in models_sell:
             yield mds
   
   
    def OperationBuyToItter(self):
        models_buy = models.OperationBuy.objects.filter(Account__bitsomail=self.bitsoMail)
        if len(models_buy) == 0:
            yield False
        for mds in models_buy:
             yield mds
    def LoggingSeparator(self, message, prf='='):
        pads = prf*15
        logging.info("%s [%s] %s", pads, message, pads)

    def LoggingOps(self,  ops, desc_limit_v=15):
        """
            cuando una operacion no cae en venta o compra se loggea en esta sección
        """
        desc_limit=desc_limit_v
        if not isinstance(ops, dict): 
            return False
        loginfo = models.OperationSellTo.objects.get(pk=ops['pk']) 
        coin=loginfo.DigitalCoin; balance=loginfo.Balance
        adquirido=loginfo.ValorCompra; Cotizado=ops['quoted_value']
        esperado=loginfo.ValorExpected; descripcion=loginfo.Description
        mail=loginfo.SendMail; Slack=loginfo.SlackHook; autosell=loginfo.AutoSell
        if len(descripcion) > desc_limit:
            descripcion=descripcion[:desc_limit_v] + '...'
        message = f"{coin} = {balance} - [Cot x {Cotizado}] - [Esperado x {esperado}] == Descripcion {descripcion} | Flags: Mail {mail} Slack {Slack} AS {autosell}"
        logging.info(message)

    def LoggingOpsbuy(self,  ops, desc_limit_v=15):
        """
            cuando una operacion no cae en venta o compra se loggea en esta sección
        """
        desc_limit=desc_limit_v
        if not isinstance(ops, dict): 
            return False
        loginfo = models.OperationBuy.objects.get(pk=ops['pk']) 
        coin=loginfo.DigitalCoin; esperado=loginfo.ValorExpected 
        Cotizado=ops['quoted_value']; descripcion=loginfo.Description
        mail=loginfo.SendMail; Slack=loginfo.SlackHook; autosell=loginfo.AutoSell
        if len(descripcion) > desc_limit:
            descripcion=descripcion[:desc_limit_v] + '...'
        message = f"{coin} Tiene un valor {Cotizado} esperamos {esperado} == Descripcion {descripcion} | Flags: Mail {mail} Slack {Slack} AS {autosell}"
        logging.info(message)

    def ListOfValidSellOperations(self):
        valid_operations = queue.Queue()
        no_sell_operations = queue.Queue()
        threads = []
        for e_op in self.OperationSellToItter():
            if e_op is False:
                return False, False
            t=sc_plugins.PluginQuoteStandardandSell(api=Sc.api, pk=e_op.pk, balance=e_op.Balance, value_expected=e_op.ValorExpected, digital_coin=e_op.DigitalCoin)
            t.PluginInitialize(valid_operations, no_sell_operations)
            threads.append(t)
            t.start()
        for tjoin in threads: tjoin.join()
        return valid_operations, no_sell_operations

    def ListOfValidBuyOperations(self):
        valid_buy_operations = queue.Queue()
        remaining_buy_ops = queue.Queue()
        threads= []
        for e_op in self.OperationBuyToItter():
            if e_op is False:
                return False, False
            t = sc_plugins.PluginQuoteBuy(api=Sc.api, pk=e_op.pk, value_expected=e_op.ValorExpected,digital_coin = e_op.DigitalCoin)
            t.PluginInitialize(valid_buy_operations, remaining_buy_ops)
            threads.append(t)
            t.start()
        for tjoin in threads: tjoin.join()
        return valid_buy_operations, remaining_buy_ops

    #Si no se usa Borrar 
    def OperationQueueToList(self, queue):
        queue_size = queue.qsize()
        list_queue = []
        if queue_size < 0:
            return False
        for i in range(queue.qsize()):
            list_queue.append(queue.get())
        return list_queue

    def OperationHandler(self):
        """
            procela el loggeo de las operaciones y devuelve un dic con 4 valores para su proceso futuro

            list_ops_pending_sell: Entrega todas las operaciones que no caen en ventas de la tabla de opsell
            lists_pending_buy: Entrega la lista de las operaciones que no son de venta
            lists_ops_buy: Entrega la lista de las operaciones de venta que tenemos pendiente
            list_ops_sells: Entrega la lista de operaciones de venta pendiente
        """
        optype= {'list_ops_pending_sell':'', 'lists_pending_buy':'',
                'lists_ops_buy':'','list_ops_sells':''}
        queue_sell_op_id, queue_no_sell_op_id = self.ListOfValidSellOperations()
        queue_buy_op_id, queue_reamining_buy_op =self.ListOfValidBuyOperations()
        if queue_sell_op_id == False and queue_no_sell_op_id == False: 
             raise ValueError("No hay operaciones Validas a procesar")
        if queue_no_sell_op_id.qsize() > 0:
            self.LoggingSeparator("OPERACIONES")
            list_ops_pending_sell=self.OperationQueueToList(queue_no_sell_op_id)
            for nosellops in list_ops_pending_sell:
                self.LoggingOps(nosellops)
            optype['list_ops_pending_sell'] = list_ops_pending_sell
        if queue_reamining_buy_op.qsize() > 0:
            self.LoggingSeparator("COMPRAS COTIZADAS")
            lists_pending_buy = self.OperationQueueToList(queue_reamining_buy_op)
            for rem in lists_pending_buy:
                self.LoggingOpsbuy(rem)
            optype['lists_pending_buy']=lists_pending_buy 
        if queue_buy_op_id.qsize() > 0:
            self.LoggingSeparator("COMPRAR")
            lists_ops_buy = self.OperationQueueToList(queue_buy_op_id)
            for buy in lists_ops_buy:
                self.LoggingOpsbuy(buy)
            optype['lists_ops_buy ']=lists_ops_buy 
        if queue_sell_op_id.qsize() > 0:
            self.LoggingSeparator("VENTAS")
            list_ops_sells=self.OperationQueueToList(queue_sell_op_id)
            for sells in list_ops_sells:
                self.LoggingOps(sells)
            optype['list_ops_sells']=list_ops_sells
        return optype


running=True
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
    while running:
        try:
            dic_operations = Sc.OperationHandler()
            time.sleep(Sc.GetConfigScanerRefresh())
        except ValueError as e:
            logging.error("%s", e.message)
            time.slee(Sc.GetConfigScanerRefresh())
        except KeyboardInterrupt:
            print("Saliendo de la aplicación")
            running=False
