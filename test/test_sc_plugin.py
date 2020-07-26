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

if __name__ == "__main__":
    unittest.main()
