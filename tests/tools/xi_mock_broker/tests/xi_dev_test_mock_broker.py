import sys
from os.path import realpath, dirname
tests_path = realpath(__file__)
sys.path.append(tests_path)
sys.path.append(dirname(tests_path) + "/../../..")  # to access 'tools' package

from tools.xi_mock_broker.xi_mock_broker import MockBroker
from tools.xi_mock_broker.xi_basic_broker import BasicBroker
import tools.xi_mock_broker.tests.paho_mqtt_client as paho_client
import tools.xi_utils as xi_utils
import unittest
import time

class TestBrokerFunctions(unittest.TestCase):

    def setUp(self):
        # self.broker = MockBroker()
        self.broker = BasicBroker()
        self.broker.on_log = xi_utils.basic_console_log

        print("Starting broker...")
        self.broker.loop_start()
        self.client = paho_client.Client()
        self.client.user_data_set("PAHO client")
        self.client.on_log = xi_utils.basic_console_log

    def tearDown(self):
        self.client.disconnect()
        self.client.loop_stop()

        self.broker.loop_stop()
        print("Broker stopped.")

    def xi_dev_test_client_connect_disconnect(self):
        self.client.connect(self.broker.bind_address[0], self.broker.bind_address[1])
        self.client.loop_start()

    def xi_dev_test_reconnect(self):
        for i in range(3):
            self.client.connect(self.broker.bind_address[0], self.broker.bind_address[1])
            self.client.loop_start()
            time.sleep(2)
            self.client.disconnect()

    def xi_dev_test_client_connect_disconnect_tls(self):
        self.broker.setup_tls("../certs/self-signed-localhost-cert.pem",
                            "../certs/self-signed-localhost-key.pem")
        self.client.tls_set("../certs/self-signed-localhost-cert.pem")
        self.client.connect(self.broker.bind_address[0], self.broker.bind_address[1])
        self.client.loop_start()

    def xi_dev_test_client_keep_alive_check(self):
        self.client.connect(self.broker.bind_address[0], self.broker.bind_address[1], 1)
        time.sleep(4)

        self.assertIsNone(self.broker.socket())


class TestPureBrokerTests(unittest.TestCase):

    def setUp(self):
        self.broker = MockBroker()
        self.broker.on_log = xi_utils.basic_console_log

    def xi_dev_test_broker_start_stop(self):
        print("Starting broker...")
        self.broker.loop_start()
        self.broker.loop_stop()
        print("Broker stopped.")

    def xi_dev_test_broker_start_stop_with_tls(self):
        self.broker.setup_tls("../certs/self-signed-localhost-cert.pem",
                            "../certs/self-signed-localhost-key.pem")

        self.broker.loop_start()
        self.broker.loop_stop()

if __name__ == "__main__":
    # unittest.main()
    loader = unittest.TestLoader()
    loader.testMethodPrefix = "xi_dev_test_"# default value is "test"

    suite = loader.discover('.', pattern = loader.testMethodPrefix + "*.py")
    unittest.TextTestRunner(verbosity=2).run(suite)
