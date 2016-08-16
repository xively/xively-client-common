import pytest

from ftests.xi_ftest_platforms_under_test import PLATFORMS_UNDER_TEST
from tools.xi_mock_broker.xi_mock_broker import MockBroker
from tools.xi_client_factory import XiClientFactory
from tools.xi_client_settings import XiClientSocketType
from tools.xi_client_settings import XiClientPlatform
from tools.xi_utils import StrictMock, Counter, basic_console_log
from tools.xi_mock_broker import mqtt_messages
from datetime import datetime
from datetime import timedelta
import queue
import ssl


class TestEssentials(object):

    def __init__(self):
        self._task_queue = queue.Queue()

    # This class only helps in encapsulating the testing essentials, such as the mock broker,
    # the client to be tested and the mock call history.
    topic = "/test_topic"
    topic_as_signed_chars = b"/test_topic"
    topic_as_bytes = bytearray(topic, "utf-8")
    control_topic_name = b'xi/ctrl/v1/unique device id/clt'
    payload_as_bytes = b"This is just a sample payload with some exotic characters &^&%$%#@"
    payload_as_string = payload_as_bytes.decode("utf-8")
    binary_payload = bytearray([0,1,1,2,3,5,8,13,21,0,34,55,89,144,0,233,255])
    client_id = "default client id"
    connection_timeout = 10
    test_timeout = 5.0

@pytest.fixture(scope="module", ids=PLATFORMS_UNDER_TEST['names'], params=PLATFORMS_UNDER_TEST['values'])
def sut_platform(request):
    # The current param is passed by py.test via the request object. Param is one value of 'params'.
    return request.param

@pytest.fixture(scope="function")
def xift(request, sut_platform):
    # Initialize client and broker
    tess = TestEssentials()
    tess.broker = MockBroker(sut_platform["socket_type"] == XiClientSocketType.WEBSOCKET)
    tess.client_sut = XiClientFactory.generate_xi_client(sut_platform["platform"], sut_platform["socket_type"])
    tess.broker.on_log = basic_console_log
    tess.sut_platform = sut_platform["platform"]

    tess.mock_call_history_client = StrictMock()
    tess.mock_call_history_broker = StrictMock()

    StrictMock.mock_broker = tess.broker
    StrictMock.client_sut = tess.client_sut

    # Mock all the callbacks
    tess.client_sut.on_connect_finish   = tess.mock_call_history_client.client.on_connect_finish
    tess.client_sut.on_disconnect       = tess.mock_call_history_client.client.on_disconnect
    tess.client_sut.on_subscribe_finish = tess.mock_call_history_client.client.on_subscribe_finish
    tess.client_sut.on_message_received = tess.mock_call_history_client.client.on_message_received
    tess.client_sut.on_publish_finish   = tess.mock_call_history_client.client.on_publish_finish

    tess.broker.on_client_connect      = tess.mock_call_history_broker.broker.on_client_connect
    tess.broker.on_client_disconnect   = tess.mock_call_history_broker.broker.on_client_disconnect
    tess.broker.on_message             = tess.mock_call_history_broker.broker.on_message
    tess.broker.on_client_subscribe    = tess.mock_call_history_broker.broker.on_client_subscribe
    tess.broker.on_client_unsubscribe  = tess.mock_call_history_broker.broker.on_client_unsubscribe

    tess.connect_options = mqtt_messages.MQTTConnectOptions(client_id=TestEssentials.client_id,
                                                            username="FTFW default username",
                                                            password="FTFW default password")

    # TearDown code
    def fin():
        tess.client_sut.stop()
        # Check that there were no unexpected calls during the test
        assert 0 == len(tess.mock_call_history_broker.caught_unexpected_calls())
        assert 0 == len(tess.mock_call_history_client.caught_unexpected_calls())

    request.addfinalizer(fin)

    return tess

def get_tls_version_to_platform(platform):
    use_tls_version = None

    try:
        # TLSv1.2 by default
        use_tls_version = ssl.PROTOCOL_TLSv1_2
        return use_tls_version
    except:
        pass

    try:
        # TLSv1.1 as a backup
        use_tls_version = ssl.PROTOCOL_TLSv1_1
        return use_tls_version
    except:
        pass

    try:
        # TLSv1.0 as a backup
        use_tls_version = ssl.PROTOCOL_TLSv1
        return use_tls_version
    except:
        pass

    raise AttributeError( "No available TLS method found")

# Usually this function ignites the test run. This method is to be called when you have everything
# set up in your test case
def act(xift, setup_default_cert=True, endpoint=None):

    if (setup_default_cert):
        # setup certs for TLS connection
        certfile = "self-signed-localhost-cert.pem"
        keyfile = "self-signed-localhost-key.pem"
        xift.client_sut.setup_tls(certfile)
        xift.broker.setup_tls("../../../xi_client_common/certs/test/" + certfile,
                              "../../../xi_client_common/certs/test/" + keyfile,
                              tls_version=get_tls_version_to_platform(xift.sut_platform))

    # Ignite
    xift.broker.loop_start()

    server_address = xift.broker.bind_address if endpoint==None else endpoint
    xift.client_sut.connect(server_address, xift.connect_options, TestEssentials.connection_timeout)

    start_datetime = datetime.now()
    timeout_reached = False

    if not xift.broker.execute(5.0):
        xift.client_sut.stop()
        pytest.fail("Test is running too long (broker timeout)!")

    if not xift.client_sut.join(5.0):
        xift.client_sut.stop()
        pytest.fail("Test is running too long (client timeout)!")

    while True:
        try:
            task = xift._task_queue.get(False)
            task()
        except queue.Empty as empty:
            break

    """
    while xift.broker._thread.is_alive() and not timeout_reached:
        try:
            timeout_reached = timedelta(0, 5) < datetime.now() - start_datetime
            task = xift._task_queue.get( True, 0.01 )
            task()
            xift._task_queue.task_done()
        except queue.Empty as ex:
            #print("exception during waiting for main thread task: " + str(ex))
            #print("timedelta = " + str(datetime.now() - start_datetime))
            pass
        except Exception as ex:
            print("+++ --- +++ exception = " + str(ex))
            xift.broker.trigger_shutdown()
            xift.client_sut.stop()
            #xift._task_queue.task_done()
            raise

    if (timeout_reached):
        xift.broker.trigger_shutdown()
        xift.client_sut.stop()
        pytest.fail("Test is running too long!")
    else:
        xift.client_sut.join()
    """
