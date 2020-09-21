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
    version="bitsoScaner ver 1"
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
    
    def InsertTickerDB(self, coin):
        book = coin+"_mxn"
        ticker = self.api.ticker(book) 
        try:
            ticker_database = models.BitsoTicker.objects.create(
                    bookname=coin,
                    ask=ticker.ask,
                    bid=ticker.bid,
                    high=ticker.high,
                    last=ticker.last,
                    low=ticker.low,
                    datetime=ticker.created_at
                    )
            ticker_database.save()
        except bitso.errors.ApiError as e:
            return False
        return True


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

    def __MessageLogGen(self, OP="sell", *args):
        """
            Entrega el mensaje a ser loggeado o enviando por algun plugin
            OP= Tipo de operacion "venta" o "compra" 
            args: como se debe acomodar la info
        """
        if OP == "sell":
            return f"{args[0]} = {args[1]} - [Cot x {args[2]}] - [Esperado x {args[3]}] == Descripcion {args[4]} | Flags: Mail {args[5]} Slack {args[6]} AS {args[7]}"
        elif OP == "buy":
            return f"{args[0]} Tiene un valor {args[1]} esperamos {args[2]} == Descripcion {args[3]} | Flags: Mail {args[4]} Slack {args[5]} AS {args[6]}"
        elif OP == "buy_alarm":
            return f"{args[0]} Tiene un valor [{args[1]}] esperamos [{args[2]}] Descripcion [{args[3]}]"
        elif OP == "sell_alarm":
            return f"{args[0]} = {args[1]} - [Cot x {args[2]}] - [Esperado x {args[3]}] == Descripcion {args[4]}"

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
        #message = f"{coin} = {balance} - [Cot x {Cotizado}] - [Esperado x {esperado}] == Descripcion {descripcion} | Flags: Mail {mail} Slack {Slack} AS {autosell}"
        message = self.__MessageLogGen("sell", coin, balance, Cotizado, esperado, descripcion, mail, Slack, autosell)
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
        #message = f"{coin} Tiene un valor {Cotizado} esperamos {esperado} == Descripcion {descripcion} | Flags: Mail {mail} Slack {Slack} AS {autosell}"
        message = self.__MessageLogGen("buy", coin, Cotizado, esperado, descripcion, mail, Slack, autosell)
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

            lists_ops_buy: Entrega la lista de las operaciones de venta que tenemos pendiente o None si no hay nada que procesar
            list_ops_sells: Entrega la lista de operaciones de venta pendiente None si no hay nada que procesar
        """
        lists_ops_buy = None; lists_ops_sells=None
        queue_sell_op_id, queue_no_sell_op_id = self.ListOfValidSellOperations()
        queue_buy_op_id, queue_reamining_buy_op =self.ListOfValidBuyOperations()
        if queue_sell_op_id == False and queue_no_sell_op_id == False: 
             raise ValueError("No hay operaciones Validas a procesar")
        if queue_no_sell_op_id.qsize() > 0:
            self.LoggingSeparator("OPERACIONES")
            list_ops_pending_sell=self.OperationQueueToList(queue_no_sell_op_id)
            for nosellops in list_ops_pending_sell:
                self.LoggingOps(nosellops)
        if queue_reamining_buy_op.qsize() > 0:
            self.LoggingSeparator("COMPRAS COTIZADAS")
            lists_pending_buy = self.OperationQueueToList(queue_reamining_buy_op)
            for rem in lists_pending_buy:
                self.LoggingOpsbuy(rem)
        if queue_buy_op_id.qsize() > 0:
            self.LoggingSeparator("COMPRAR")
            lists_ops_buy = self.OperationQueueToList(queue_buy_op_id)
            for buy in lists_ops_buy:
                self.LoggingOpsbuy(buy)
        if queue_sell_op_id.qsize() > 0:
            self.LoggingSeparator("VENTAS")
            lists_ops_sells=self.OperationQueueToList(queue_sell_op_id)
            for sells in lists_ops_sells:
                self.LoggingOps(sells)
        return lists_ops_buy, lists_ops_sells 
    
    def AlarmBuyTrueOrFalse(self,_pk):
        alarm_status=models.OperationBuy.objects.get(pk=_pk)
        return alarm_status.SlackHook, alarm_status.SendMail
    
    def AlarmSellTrueOrFalse(self,_pk):
        alarm_status=models.OperationSellTo.objects.get(pk=_pk)
        return alarm_status.SlackHook, alarm_status.SendMail

    def __AlarmSystemMessage(self,alarms, op="buy"):
        alarm_system_slack = 0
        alarm_system_mail = 0
        info_operation=None; message=None
        slack_alarm = mail_alarms = None
        slack_alarm_t = sc_plugins.PluginSlackAlarm(self.version)
        mail_alarm_t = sc_plugins.PluginMailAlarm(self.version)
        conf_webhook = models.SlackWebHook.objects.filter(BitsoAcount__bitsomail=self.bitsoMail).last().hook
        mail_data=models.SenderMailAccount.objects.filter(BitsoAcount__bitsomail=self.bitsoMail).last()
        slack_alarm_t.PluginInitialize(conf_webhook)
        mail_alarm_t.PluginInitialize(sender=mail_data.MailAccount, receivers=mail_data.MailReceivers, sender_password=mail_data.MailKey, subject=self.version)
        for ops in alarms:
            #slack_alarm, mail_alarms = self.AlarmBuyTrueOrFalse(ops['pk'])
            if op == "buy":
                slack_alarm, mail_alarms = self.AlarmBuyTrueOrFalse(ops['pk'])
                info_operation = models.OperationBuy.objects.get(pk=ops['pk'])
                coin=info_operation.DigitalCoin; esperado=info_operation.ValorExpected 
                Cotizado=ops['quoted_value']; descripcion=info_operation.Description
                message = self.__MessageLogGen("buy_alarm", coin, Cotizado, esperado, descripcion)
            elif op == "sell":
                slack_alarm, mail_alarms = self.AlarmSellTrueOrFalse(ops['pk'])
                info_operation = models.OperationSellTo.objects.get(pk=ops['pk'])
                coin=info_operation.DigitalCoin; balance= info_operation.Balance; Cotizado=ops['quoted_value']
                esperado = info_operation.ValorExpected; descripcion = info_operation.Description
                message = self.__MessageLogGen("sell_alarm", coin, balance,Cotizado, esperado, descripcion)
            else:
                return None, None
            if slack_alarm:
                slack_alarm_t.AppendMessage(message)
                alarm_system_slack+=1
            if mail_alarms:
                mail_alarm_t.AppendMessage(message)
                alarm_system_mail+=1
        if alarm_system_slack == 0:
            slack_alarm_t = None
        if alarm_system_mail==0:
            mail_alarm_t = None
        return slack_alarm_t, mail_alarm_t

    def AlarmSystem(self, alarms_buys, alarms_sells):
        err_buys=0; err_sells=0 
        if alarms_buys is None:
            logging.warning("No buys alarms")
            err_buys = 1
        else:
            slack_alarm_exec, mail_alarm_exec = self.__AlarmSystemMessage(alarms_buys, "buy")
            if slack_alarm_exec != None:
                print('Slack Alrm')
                slack_alarm_exec.start()
                #slack_alarm_exec.join()
            else:
                logging.debug("Not possible to send Slack Message None Return")
            if mail_alarm_exec != None:
                mail_alarm_exec.start()
                #mail_alarm_exec.join()
            else:
                logging.debug("Not possible to send Mail Message None Return")
        if alarms_sells is None:
            logging.warning("No sells alarms")
            err_sells = 1
        else:
            slack_alarm_exec, mail_alarm_exec = self.__AlarmSystemMessage(alarms_sells, "sell")
            if slack_alarm_exec != None:
                print('Slack Alrm')
                slack_alarm_exec.start()
                #slack_alarm_exec.join()
            else:
                logging.debug("Not possible to send Slack Message None Return")
            if mail_alarm_exec != None:
                mail_alarm_exec.start()
                #mail_alarm_exec.join()
            else:
                logging.debug("Not possible to send Mail Message None Return")
        if err_buys and err_sells:
            return False

    def Auto_Sell_Buy(self, alarms_sell, alarsm_buy):
        err_sell = 0
        if alarms_sell is None:
            err_sell = 1
            logging.debug("AutoSell not Operations")


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
    for bal in models.OperationAction.SupportedCoins:
        if not Sc.InsertTickerDB(bal[0]):
            logging.error("Imposible to retrive ticker info coin %s", bal[0])
    while running:
        try:
            lists_compras, lists_ventas = Sc.OperationHandler()
            print(f"lists compras {lists_compras} lists ventas {lists_ventas}")
            Sc.AlarmSystem(lists_compras, lists_ventas)
            #Sistema de Aalarms como Slack y el mail
            time.sleep(Sc.GetConfigScanerRefresh())
        except ValueError as e:
            logging.error("%s", e)
            time.sleep(Sc.GetConfigScanerRefresh())
        except KeyboardInterrupt:
            print("Saliendo de la aplicación")
            running=False
