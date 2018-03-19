# Copyright (c) 2012-2014 Xively
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v1.0
# and Eclipse Distribution License v1.0 which accompany this distribution.
#
# The Eclipse Public License is available at
#    http://www.eclipse.org/legal/epl-v10.html
# and the Eclipse Distribution License is available at
#   http://www.eclipse.org/org/documents/edl-v10.php.
#
# Contributors:
#    Roger Light - initial API and implementation

"""
These are MQTT protocol related utilities and data structures.
"""

import sys
import struct

MQTTv31 = 3
MQTTv311 = 4

if sys.version_info[0] < 3:
    PROTOCOL_NAMEv31 = "MQIsdp"
    PROTOCOL_NAMEv311 = "MQTT"
else:
    PROTOCOL_NAMEv31 = b"MQIsdp"
    PROTOCOL_NAMEv311 = b"MQTT"

PROTOCOL_VERSION = 3


# Message types
CONNECT = 0x10
CONNACK = 0x20
PUBLISH = 0x30
PUBACK = 0x40
PUBREC = 0x50
PUBREL = 0x60
PUBCOMP = 0x70
SUBSCRIBE = 0x80
SUBACK = 0x90
UNSUBSCRIBE = 0xA0
UNSUBACK = 0xB0
PINGREQ = 0xC0
PINGRESP = 0xD0
DISCONNECT = 0xE0

# CONNECT flags
USERNAME_FLAG = 0x80
PASSWORD_FLAG = 0x40
WILL_RETAIN_FLAG = 0x20
WILL_QOS_FLAG = 0x18
WILL_FLAG = 0x04
CLEAN_SESSION_FLAG = 0x02

# Log levels
MQTT_LOG_INFO = 0x01
MQTT_LOG_NOTICE = 0x02
MQTT_LOG_WARNING = 0x04
MQTT_LOG_ERR = 0x08
MQTT_LOG_DEBUG = 0x10

# CONNACK codes
CONNACK_ACCEPTED = 0
CONNACK_REFUSED_PROTOCOL_VERSION = 1
CONNACK_REFUSED_IDENTIFIER_REJECTED = 2
CONNACK_REFUSED_SERVER_UNAVAILABLE = 3
CONNACK_REFUSED_BAD_USERNAME_PASSWORD = 4
CONNACK_REFUSED_NOT_AUTHORIZED = 5

# Message state
mqtt_ms_invalid = 0
mqtt_ms_publish= 1
mqtt_ms_wait_for_puback = 2
mqtt_ms_wait_for_pubrec = 3
mqtt_ms_resend_pubrel = 4
mqtt_ms_wait_for_pubrel = 5
mqtt_ms_resend_pubcomp = 6
mqtt_ms_wait_for_pubcomp = 7
mqtt_ms_send_pubrec = 8
mqtt_ms_queued = 9

# Error values
MQTT_ERR_AGAIN = -1
MQTT_ERR_SUCCESS = 0
MQTT_ERR_NOMEM = 1
MQTT_ERR_PROTOCOL = 2
MQTT_ERR_INVAL = 3
MQTT_ERR_NO_CONN = 4
MQTT_ERR_CONN_REFUSED = 5
MQTT_ERR_NOT_FOUND = 6
MQTT_ERR_CONN_LOST = 7
MQTT_ERR_TLS = 8
MQTT_ERR_PAYLOAD_SIZE = 9
MQTT_ERR_NOT_SUPPORTED = 10
MQTT_ERR_AUTH = 11
MQTT_ERR_ACL_DENIED = 12
MQTT_ERR_UNKNOWN = 13
MQTT_ERR_ERRNO = 14


class MQTTMessage:
    """ This is a class that describes an incoming message. It is passed to the
    on_message callback as the message parameter.

    Members:

    topic : String. topic that the message was published on.
    payload : String/bytes the message payload.
    qos : Integer. The message Quality of Service 0, 1 or 2.
    retain : Boolean. If true, the message is a retained message and not fresh.
    mid : Integer. The message id.
    """
    def __init__(self):
        self.timestamp = 0
        self.state = mqtt_ms_invalid
        self.dup = False
        self.mid = 0
        self.topic = ""
        self.payload = None
        self.qos = 0
        self.retain = False


class MQTTConnectOptions(object):
    """ This class represents the connect options available for an MQTT client on connection time.

    Members:

    protocol_version: version number of the desired MQTT protocol.
    protocol_name: name of the desired MQTT protocol
    connect_flags: MQTT connect flags (Clean session, will, will QoS, will retain, username, password)
    keep_alive: Keep-Alive period for the connection
    client_id: MQTT client ID of the connecting device
    username: device username (optional)
    password: device secret (optional)
    will_topic: will topic
    will_message: payload of the will message
    will_qos: QoS of the will message
    """

    def __init__(self, protocol_name=PROTOCOL_NAMEv311, protocol_version=MQTTv311, connect_flags=0,
                 keep_alive=60, client_id="", username="", password="", will_topic="", will_message=""):
        self.protocol_name = protocol_name
        self.protocol_version = protocol_version
        self.connect_flags = connect_flags
        self.keep_alive = keep_alive
        self.client_id = client_id
        self.username = username
        self.password = password
        self.will_topic = will_topic
        self.will_message = will_message

    @classmethod
    def from_mqtt_packet(cls, packet):
        copts = MQTTConnectOptions()
        (copts.protocol_name, copts.protocol_version, copts.connect_flags, copts.keep_alive, copts.client_id,
         copts.username, copts.password, copts.will_topic, copts.will_message) = MQTTConnectOptions.decode_connect_packet(packet)
        return copts

        (self.protocol_name, self.protocol_version, self.connect_flags, self.keep_alive, self.client_id,
         self.username, self.password, self.will_topic, self.will_message) = MQTTConnectOptions.decode_connect_packet(packet)

    @staticmethod
    def decode_connect_packet(packet):
        (protocol_name, rest) = MQTTConnectOptions.process_utf8_word_from_stream(packet)
        rest_length = len(rest) - 4
        pack_format = "!BBH{0}s".format(rest_length)
        (proto_ver, connect_flags, keep_alive, rest) = struct.unpack(pack_format, rest)

        (client_id, rest) = MQTTConnectOptions.process_utf8_word_from_stream(rest)

        username = None
        password = None
        will_topic = None
        will_message = None

        if connect_flags & WILL_FLAG:
            (will_topic, rest) = MQTTConnectOptions.process_utf8_word_from_stream(rest)
            (will_message, rest) = MQTTConnectOptions.process_utf8_word_from_stream(rest)

        if connect_flags & USERNAME_FLAG:
            (username, rest) = MQTTConnectOptions.process_utf8_word_from_stream(rest)

        if connect_flags & PASSWORD_FLAG:
            (password, rest) = MQTTConnectOptions.process_utf8_word_from_stream(rest)

        return protocol_name, proto_ver, connect_flags, keep_alive, client_id, username, password, will_topic, will_message

    @staticmethod
    def process_utf8_word_from_stream(stream):
        stream_length = len(stream)
        if stream_length < 2:
            raise Exception("Invalid stream! Failed to process UTF-8 encoded string from stream!")
        pack_format = "!H{0}s".format(stream_length - 2)
        (word_length, rest) = struct.unpack(pack_format, stream)
        stream_length = len(rest)
        if stream_length < word_length:
            raise Exception("Corrupted stream! Failed to read UTF-8 encoded string!")
        pack_format = str(word_length) + "s"
        if stream_length > word_length:
            pack_format += str(stream_length - word_length) + "s"
            (word, rest) = struct.unpack(pack_format, rest)
        else:
            # The result of unpack is always a tuple, but we only expect one string as a result
            word = struct.unpack(pack_format, rest)[0]
            rest = None

        return word, rest
