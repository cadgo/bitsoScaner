#!/usr/bin/env python3
import django, os, time
from plugins import sc_plugins
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangobitso.settings')
django.setup()
from django.core.exceptions import ObjectDoesNotExist
from bitsoScaner import models
import sys, logging, threading
import bitso, threading

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

    def SupportedCoins(self):
        """
            Rertun the list of supported coins or None si esta vacia
        """
        coins = []
        supCoins = models.OperationBuy.SupportedCoins
        if len(supCoins) == 0:
            raise ValueError('There is not supported coins to continue')
        for x in supCoins:
            coins.append(x[0])
        return coins


if __name__ == '__main__':
    if len(sys.argv) < 1:
        print("Se requiere una cuenta valida para continuar")
        sys.exit()
    Sc=Scanner(sys.argv[1])
    key, password = Sc.GetBitsoKeyPass()
    #print(f"key {key} pass {password}")
    ca = Sc.BitsoLogin(key, password)
    if not ca: 
        logging.error("No fue posible loggearse a bitso con las credenciales")
    else:
        Sc.api = ca
    coins = Sc.SupportedCoins()
    thread_Balance = sc_plugins.BalanceUpdater(api=ca)
    thread_Balance.SupportedCoins = coins
    thread_Balance.start()
    while True:
       time.sleep(30)
    
