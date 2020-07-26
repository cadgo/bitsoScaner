import sys,bitso, queue
from django.test import TestCase
from bitsoScaner import models
sys.path.insert(1, "../")
from tscanner import Scanner

"""
    Mover a la carpeta test una vez finalizadas las pruebas
"""


mail_test = "prueba@test.om"
class ts_scanner_isValidAccount(TestCase):
    def setUp(self):
        global mail_test 
        models.BitsoAcount.objects.create(bitsomail=mail_test, bitsokey='aaaaaaa', bitsosecret="bbbbbbbbbbbbb")
        self.sc = Scanner(mail_test)

    def test_isValidAccount(self):
        global mail_test
        self.assertTrue(self.sc._isValidaAccount(mail_test))
        self.assertFalse(self.sc._isValidaAccount('test@fail.com'))
        self.assertFalse(self.sc._isValidaAccount(''))

class ts_scanner_GetBitsoKeyPass(TestCase):
    def setUp(self):
        global mail_test
        models.BitsoAcount.objects.create(bitsomail=mail_test, bitsokey='aaaaaaa', bitsosecret="bbbbbbbbbbbbb")
        models.BitsoAcount.objects.create(bitsomail="mail2@test", bitsokey='', bitsosecret="")
        self.sc = Scanner(mail_test)
        self.sc2= Scanner("mail2@test")

    def test_GetBitsoKeyPass(self):
        key = models.BitsoAcount.objects.get(bitsomail=mail_test).bitsokey
        password = models.BitsoAcount.objects.get(bitsomail=mail_test).bitsosecret
        tkey, tpass =self.sc.GetBitsoKeyPass()
        print(f"-----{key}--------")
        self.assertEqual(key, tkey)
        print(f"-----{password}--------")
        self.assertEqual(password, tpass)


    def test_GetBitsoKeyPass_empty(self):
        print("test_GetBitsoKeyPass_empty")
        ret1, ret2 = self.sc2.GetBitsoKeyPass()
        self.assertFalse(ret1)
        self.assertFalse(ret2)
        
class ts_RunBalancePlugin(TestCase):
    def setUp(self):
        global mail_test 
        models.BitsoAcount.objects.create(bitsomail=mail_test, bitsokey='aaaaaaa', bitsosecret="bbbbbbbbbbbbb")
        apitest=bitso.Api('er','ppp')
        self.sc = Scanner(mail_test)
        self.sc.api=apitest
    
    def test_RunBalacePlugin(self):
        aa = self.sc.RunBalancePlugin(('btc', 'xrp', 'eth'))
        self.assertTrue( isinstance(aa, queue.Queue))
        print(aa)
