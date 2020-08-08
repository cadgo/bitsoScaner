#!/usr/bin/env python3
import unittest
import sys
sys.path.insert(1, '../plugins')
import sc_plugins
import threading, queue, bitso

class TestPlugins(unittest.TestCase):
    def setUp(self):
        self.test1=sc_plugins.BalanceUpdater(api=bitso.Api(), desc='asdasdas')
    
    def test_PluginApiInstance(self):
        with self.assertRaises(ValueError) as context:
            sc_plugins.BalanceUpdater(api='', desc='adasdasdas')
        print(context.exception)

    def test_PluginInitialize(self):
        self.assertEqual(self.test1.PluginInitialize('btc', queue.Queue()), True)
        with self.assertRaises(ValueError) as context:
            self.test1.PluginInitialize('', queue.Queue())
        #self.assertEqual(self.test1.PluginInitialize('btc', ''), ValueError)
        print(context.exception)

        with self.assertRaises(ValueError) as context:
            self.test1.PluginInitialize('btc', 0)
        #self.assertEqual(self.test1.PluginInitialize('btc', ''), ValueError)
        print(context.exception)


class TestPlugins_QuoteBuy(unittest.TestCase):
    
    def test_plugin_init(self):
        print("Prueba con pk 0 y value_expected 0")
        with self.assertRaises(ValueError) as context:
            sc_plugins.PluginQuoteBuy(api=bitso.Api(), value_expected=0,pk=0, digital_coin="")
        print(context.exception)

        #PK = 0
        print("Prueba con solo pk en cero")
        with self.assertRaises(ValueError) as context:
            sc_plugins.PluginQuoteBuy(api=bitso.Api(), value_expected=0,pk=1,digital_coin="btc")
        print(context.exception)
        
        #PK = 0
        print("Prueba con solo value_expected en cero")
        with self.assertRaises(ValueError) as context:
            sc_plugins.PluginQuoteBuy(api=bitso.Api(), value_expected=1,pk=0,digital_coin="btc")
        print(context.exception)

if __name__ == "__main__":
    unittest.main()
