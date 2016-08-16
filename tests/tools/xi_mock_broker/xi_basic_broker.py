import sys
import time

from os.path import realpath, dirname
tests_path = realpath(__file__)
sys.path.append(tests_path)
sys.path.append(dirname(tests_path) + "/../..")  # to access 'tools' package

from tools.xi_mock_broker.mqtt_messages import MQTT_ERR_SUCCESS, MQTT_ERR_CONN_LOST, MQTT_LOG_WARNING
from tools.xi_mock_broker.xi_mock_broker import MockBroker, MQTTConnectionState, mqtt_ms_wait_for_puback, \
    mqtt_ms_wait_for_pubcomp, mqtt_ms_wait_for_pubrec, mqtt_ms_wait_for_pubrel


# The basic broker has the following abilities:
#   * it accepts all the incoming connections
#   * it accepts all subscribe attempts
#   * it responds to each ping request immediately
#   * it disconnects the client, if its keep-alive timer expires
class BasicBroker(MockBroker):
    def __init__(self):
        super(BasicBroker, self).__init__()
        self._userdata = "Basic Broker"
        self._message_retry = 20
        self._last_retry_check = 0
        self.on_message_filtered = []

    def _handle_on_message(self, message):
        self._callback_mutex.acquire()
        matched = False
        for t in self.on_message_filtered:
            if self.topic_matches_sub(t[0], message.topic):
                self._in_callback = True
                t[1](self, self._userdata, message)
                self._in_callback = False
                matched = True

        if not matched and self.on_message:
            self._in_callback = True
            self.on_message(self, self._userdata, message)
            self._in_callback = False

        self._callback_mutex.release()

    def message_retry_set(self, retry):
        """Set the timeout in seconds before a message with QoS>0 is retried.
        20 seconds by default."""
        if retry < 0:
            raise ValueError('Invalid retry.')

        self._message_retry = retry

    def loop_misc(self):
        """Process miscellaneous network events. Use in place of calling loop() if you
        wish to call select() or equivalent on.

        Do not use if you are using the threaded interface loop_start()."""
        ret = super(BasicBroker, self).loop_misc()
        if ret != MQTT_ERR_SUCCESS:
            return ret

        now = time.time()

        if not self._check_keep_alive():
            return MQTT_ERR_CONN_LOST

        if self._last_retry_check + 1 < now:
            # Only check once a second at most
            self._message_retry_check()
            self._last_retry_check = now

        return MQTT_ERR_SUCCESS

    def message_callback_add(self, sub, callback):
        """Register a message callback for a specific topic.
        Messages that match 'sub' will be passed to 'callback'. Any
        non-matching messages will be passed to the default on_message
        callback.

        Call multiple times with different 'sub' to define multiple topic
        specific callbacks.

        Topic specific callbacks may be removed with
        message_callback_remove()."""
        if callback is None or sub is None:
            raise ValueError("sub and callback must both be defined.")

        self._callback_mutex.acquire()

        for i in range(0, len(self.on_message_filtered)):
            if self.on_message_filtered[i][0] == sub:
                self.on_message_filtered[i] = (sub, callback)
                self._callback_mutex.release()
                return

        self.on_message_filtered.append((sub, callback))
        self._callback_mutex.release()

    def message_callback_remove(self, sub):
        """Remove a message callback previously registered with
        message_callback_add()."""
        if sub is None:
            raise ValueError("sub must defined.")

        self._callback_mutex.acquire()
        for i in range(0, len(self.on_message_filtered)):
            if self.on_message_filtered[i][0] == sub:
                self.on_message_filtered.pop(i)
                self._callback_mutex.release()
                return
        self._callback_mutex.release()

    @staticmethod
    def topic_matches_sub(sub, topic):
        """Check whether a topic matches a subscription.

        For example:

        foo/bar would match the subscription foo/# or +/bar
        non/matching would not match the subscription non/+/+
        """
        result = True
        multilevel_wildcard = False

        slen = len(sub)
        tlen = len(topic)

        if slen > 0 and tlen > 0:
            if (sub[0] == '$' and topic[0] != '$') or (topic[0] == '$' and sub[0] != '$'):
                return False

        spos = 0
        tpos = 0

        while spos < slen and tpos < tlen:
            if sub[spos] == topic[tpos]:
                if tpos == tlen-1:
                    # Check for e.g. foo matching foo/#
                    if spos == slen-3 and sub[spos+1] == '/' and sub[spos+2] == '#':
                        result = True
                        multilevel_wildcard = True
                        break

                spos += 1
                tpos += 1

                if tpos == tlen and spos == slen-1 and sub[spos] == '+':
                    spos += 1
                    result = True
                    break
            else:
                if sub[spos] == '+':
                    spos += 1
                    while tpos < tlen and topic[tpos] != '/':
                        tpos += 1
                    if tpos == tlen and spos == slen:
                        result = True
                        break

                elif sub[spos] == '#':
                    multilevel_wildcard = True
                    if spos+1 != slen:
                        result = False
                        break
                    else:
                        result = True
                        break

                else:
                    result = False
                    break

        if not multilevel_wildcard and (tpos < tlen or spos < slen):
            result = False

        return result

    # ============================================================
    # Private functions
    # ============================================================

    def _check_keep_alive(self):
        now = time.time()
        self._msgtime_mutex.acquire()
        last_msg_in = self._last_msg_in
        self._msgtime_mutex.release()
        if (self._sock is not None or self._ssl is not None) and (now - last_msg_in >= self._keep_alive * 1.5):
            self._easy_log(MQTT_LOG_WARNING, "Client disconnected due to keep-alive timeout!")
            self._close_client_socket()
            if self._state == MQTTConnectionState.DISCONNECTING:
                rc = MQTT_ERR_SUCCESS
            else:
                rc = 1
            self._callback_mutex.acquire()
            if self.on_client_disconnect:
                self._in_callback = True
                self.on_client_disconnect(self, self._userdata, rc)
                self._in_callback = False
            self._callback_mutex.release()

            return False

        # Client is still alive
        return True

    def _message_retry_check_actual(self, messages, mutex):
        mutex.acquire()
        now = time.time()
        for m in messages:
            if m.timestamp + self._message_retry < now:
                if m.state == mqtt_ms_wait_for_puback or m.state == mqtt_ms_wait_for_pubrec:
                    m.timestamp = now
                    m.dup = True
                    self._send_publish(m.mid, m.topic, m.payload, m.qos, m.retain, m.dup)
                elif m.state == mqtt_ms_wait_for_pubrel:
                    m.timestamp = now
                    m.dup = True
                    self._send_pubrec(m.mid)
                elif m.state == mqtt_ms_wait_for_pubcomp:
                    m.timestamp = now
                    m.dup = True
                    self._send_pubrel(m.mid, True)
        mutex.release()

    def _message_retry_check(self):
        self._message_retry_check_actual(self._out_messages, self._out_message_mutex)
        self._message_retry_check_actual(self._in_messages, self._in_message_mutex)


if __name__ == "__main__":
    import tools.xi_utils as xi_utils
    broker = BasicBroker()
    broker.on_log = xi_utils.basic_console_log
    broker.loop_start()

    print("Type \'q\' to quit...\n")

    while True:
        ch = sys.stdin.read(1)
        if ch == 'q':
            print("Broker stopping")
            broker.loop_stop()
            break
        else:
            print(ch)

    print("Exiting")
