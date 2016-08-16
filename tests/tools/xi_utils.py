"""
Utility classes for functional testing.
"""
import sys
import pytest
import traceback
import threading
from tools.xi_mock_broker import mqtt_messages

python2 = sys.version_info[0] < 3
if python2:
    from mock import MagicMock
else:
    from unittest.mock import MagicMock


# Small utility class mainly for closure functions in mocks
class Counter(object):
    def __init__(self):
        self.count = 0

    def inc(self):
        self.count += 1

    def get(self):
        return self.count

    def is_at(self, n):
        return self.count == n


# This mock class is strict in that terms that it will raise an exception when it is called unexpectedly.
class StrictMock(MagicMock):
    mock_broker = None
    client_sut = None

    def __init__(self, *args, **kwargs):
        MagicMock.__init__(self, *args, **kwargs)

        self._unexpected_calls_mutex = threading.Lock()
        self._unexpected_calls = []

        self._stored_name = None
        if 'name' in kwargs:
            self._stored_name = kwargs['name']

        # Do not raise an exception if this mock object (let's say 'apple' is the name of this mock) is used in
        # "if apple:"-like expressions.
        # I know the most correct way would be to check non-None-ness like
        # "if apple is not None:"
        # but often python coders are just lazy doing so. (For instance they are also lazy in the PAHO python MQTT
        # client implementation.)
        if 'name' not in kwargs or \
                (kwargs['name'] != '__bool__' and kwargs['name'] != '__nonzero__' and kwargs['name'] != 'mock.__bool__'):

            def strict_side_effect(*x):
                self.mock_broker.trigger_shutdown()
                self.client_sut.stop()
                self._unexpected_call()
                #Exception("Unexpected call: " + str(kwargs))
                pytest.fail("\n[ StrictMock ] Unexpected call: " + str(kwargs))

            self.side_effect = strict_side_effect

    def _mock_call(self, *args, **kwargs):
        if self._stored_name is not None and \
                        '__bool__' in self._stored_name or '__nonzero__' in self._stored_name:
            # Return here so that bool type calls are not recorded in the mock call history.
            return self is not None
        # FIXME - This line unfortunately breaks python 2.7 compatibility, because 4 args are expected here in python 2.7.
        return MagicMock._mock_call(self, *args, **kwargs)

    def _unexpected_call(self):
        # Record the unexpected call in the parent mock. Get there recursively.
        if self._mock_parent is not None:
            return self._mock_parent._unexpected_call()

        try:
            self._unexpected_calls_mutex.acquire()
            self._unexpected_calls.append(traceback.extract_stack())
            #print("\n\n ****************** Unexpected call! Stack trace:\n")
            #traceback.print_stack()
            #print(self._unexpected_calls)
        finally:
            self._unexpected_calls_mutex.release()
            # raise Exception("Unexpected call!")

    def caught_unexpected_calls(self):
        try:
            self._unexpected_calls_mutex.acquire()
            return self._unexpected_calls
        finally:
            self._unexpected_calls_mutex.release()



# Basic console logger
def basic_console_log(caller, userdata, log_level, message):
    if userdata is not None:
        print(userdata + " [" + threading.current_thread().getName() + "]: " + message)
    else:
        print(message)

# Basic Message Matcher checks to see if the topic, qos_level and payload all match.
class BasicMessageMatcher(mqtt_messages.MQTTMessage):
    def __init__(self, topic, qos_level, payload, dup = 0):
        super(BasicMessageMatcher, self).__init__()
        self._topic = topic
        self._qos_level = qos_level
        self._payload = payload
        self._dup = dup

    def __eq__(self, other):
        #print("*************************** " + str(self._payload) + ", " + str(other.payload))
        #print("*************************** " + self._topic + ", " + other.topic)
        #print("*************************** " + str(self._qos_level) + ", " + str(other.qos))
        #print("****** other dup ********** " + str(self._dup) + ", " + str(other.dup))

        payloads_match_or_no_need_to_check = self._payload == None or self._payload == other.payload

        return self._topic == other.topic and \
               self._qos_level == other.qos and \
               payloads_match_or_no_need_to_check and \
               self._dup == other.dup
