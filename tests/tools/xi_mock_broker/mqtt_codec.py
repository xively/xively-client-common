# Copyright (c) 2012-2015 Xively
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
#    Roger Light <roger@atchoo.org> - initial API and implementation

"""
This is an MQTT v3.1.1 encoder/decoder.
"""

import errno
import platform
import socket

from tools.xi_mock_broker.mqtt_messages import *  # FIXME - don't import everything

HAVE_SSL = True
try:
    import ssl
    cert_reqs = ssl.CERT_REQUIRED
    tls_version = ssl.PROTOCOL_TLSv1
except:
    HAVE_SSL = False
    cert_reqs = None
    tls_version = None
import struct
import sys
import threading

HAVE_DNS = True
try:
    import dns.resolver
except ImportError:
    HAVE_DNS = False

if platform.system() == 'Windows':
    EAGAIN = errno.WSAEWOULDBLOCK
else:
    EAGAIN = errno.EAGAIN


class MQTTCodec(object):

    def __init__(self, socket, ssl_socket):
        self._userdata = "MQTT Codec"

        self._in_packet = {
            "command": 0,
            "have_remaining": 0,
            "remaining_count": [],
            "remaining_mult": 1,
            "remaining_length": 0,
            "packet": b"",
            "to_process": 0,
            "pos": 0}
        self._sock = socket
        self._ssl = ssl_socket

        self.on_log = None

        self._out_packet_mutex = threading.Lock()
        self._current_out_packet_mutex = threading.Lock()

        self.on_packet_encoded = None
        self.on_packet_decoded = None

    def __del__(self):
        pass

    def decode_packet(self):
        # This gets called if pselect() indicates that there is network data
        # available - ie. at least one byte.  What we do depends on what data we
        # already have.
        # If we've not got a command, attempt to read one and save it. This should
        # always work because it's only a single byte.
        # Then try to read the remaining length. This may fail because it is may
        # be more than one byte - will need to save data pending next read if it
        # does fail.
        # Then try to read the remaining payload, where 'payload' here means the
        # combined variable header and actual payload. This is the most likely to
        # fail due to longer length, so save current data and current position.
        # After all data is read, send to _mqtt_handle_packet() to deal with.
        # Finally, free the memory and reset everything to starting conditions.
        if self._in_packet['command'] == 0:
            try:
                if self._ssl:
                    command = self._ssl.read(1)
                else:
                    command = self._sock.recv(1)
            except socket.error as err:
                if self._ssl and (err.errno == ssl.SSL_ERROR_WANT_READ or err.errno == ssl.SSL_ERROR_WANT_WRITE):
                    return MQTT_ERR_AGAIN
                if err.errno == EAGAIN:
                    return MQTT_ERR_AGAIN
                print(err)
                return 1
            else:
                if len(command) == 0:
                    return 1
                command = struct.unpack("!B", command)
                self._in_packet['command'] = command[0]

        if self._in_packet['have_remaining'] == 0:
            # Read remaining
            # Algorithm for decoding taken from pseudo code at
            # http://publib.boulder.ibm.com/infocenter/wmbhelp/v6r0m0/topic/com.ibm.etools.mft.doc/ac10870_.htm
            while True:
                try:
                    if self._ssl:
                        byte = self._ssl.read(1)
                    else:
                        byte = self._sock.recv(1)
                except socket.error as err:
                    if self._ssl and (err.errno == ssl.SSL_ERROR_WANT_READ or err.errno == ssl.SSL_ERROR_WANT_WRITE):
                        return MQTT_ERR_AGAIN
                    if err.errno == EAGAIN:
                        return MQTT_ERR_AGAIN
                    print(err)
                    return 1
                else:
                    byte = struct.unpack("!B", byte)
                    byte = byte[0]
                    self._in_packet['remaining_count'].append(byte)
                    # Max 4 bytes length for remaining length as defined by protocol.
                    # Anything more likely means a broken/malicious client.
                    if len(self._in_packet['remaining_count']) > 4:
                        return MQTT_ERR_PROTOCOL

                    self._in_packet['remaining_length'] = self._in_packet['remaining_length'] + (byte & 127)*self._in_packet['remaining_mult']
                    self._in_packet['remaining_mult'] = self._in_packet['remaining_mult'] * 128

                if (byte & 128) == 0:
                    break

            self._in_packet['have_remaining'] = 1
            self._in_packet['to_process'] = self._in_packet['remaining_length']

        while self._in_packet['to_process'] > 0:
            try:
                if self._ssl:
                    data = self._ssl.read(self._in_packet['to_process'])
                else:
                    data = self._sock.recv(self._in_packet['to_process'])
            except socket.error as err:
                if self._ssl and (err.errno == ssl.SSL_ERROR_WANT_READ or err.errno == ssl.SSL_ERROR_WANT_WRITE):
                    return MQTT_ERR_AGAIN
                if err.errno == EAGAIN:
                    return MQTT_ERR_AGAIN
                print(err)
                return 1
            else:
                self._in_packet['to_process'] = self._in_packet['to_process'] - len(data)
                self._in_packet['packet'] = self._in_packet['packet'] + data

        # All data for this packet is read and decoded.
        self._in_packet['pos'] = 0
        rc = self.on_packet_decoded(self._in_packet)

        # Free data and reset values
        self._in_packet = dict(
            command=0,
            have_remaining=0,
            remaining_count=[],
            remaining_mult=1,
            remaining_length=0,
            packet=b"",
            to_process=0,
            pos=0)

        return rc

    def encode_publish(self, mid, topic, payload=None, qos=0, retain=False, dup=False):
        utopic = topic.encode('utf-8')
        command = PUBLISH | ((dup&0x1)<<3) | (qos<<1) | retain
        packet = bytearray()
        packet.extend(struct.pack("!B", command))
        if payload is None:
            remaining_length = 2+len(utopic)
            self._easy_log(MQTT_LOG_DEBUG, "Sending PUBLISH (d"+str(dup)+", q"+str(qos)+", r"+str(int(retain))+", m"+str(mid)+", '"+topic+"' (NULL payload)")
        else:
            if isinstance(payload, str):
                upayload = payload.encode('utf-8')
                payloadlen = len(upayload)
            elif isinstance(payload, bytearray):
                payloadlen = len(payload)
            elif isinstance(payload, unicode):
                upayload = payload.encode('utf-8')
                payloadlen = len(upayload)

            remaining_length = 2+len(utopic) + payloadlen
            self._easy_log(MQTT_LOG_DEBUG, "Sending PUBLISH (d"+str(dup)+", q"+str(qos)+", r"+str(int(retain))+", m"+str(mid)+", '"+topic+"', ... ("+str(payloadlen)+" bytes)")

        if qos > 0:
            # For message id
            remaining_length = remaining_length + 2

        self._pack_remaining_length(packet, remaining_length)
        self._pack_str16(packet, topic)

        if qos > 0:
            # For message id
            packet.extend(struct.pack("!H", mid))

        if payload is not None:
            if isinstance(payload, str):
                pack_format = str(payloadlen) + "s"
                packet.extend(struct.pack(pack_format, upayload))
            elif isinstance(payload, bytearray):
                packet.extend(payload)
            elif isinstance(payload, unicode):
                pack_format = str(payloadlen) + "s"
                packet.extend(struct.pack(pack_format, upayload))
            else:
                raise TypeError('payload must be a string, unicode or a bytearray.')

        return self.on_packet_encoded(PUBLISH, packet, mid, qos)

    def encode_pubrec(self, mid):
        self._easy_log(MQTT_LOG_DEBUG, "Sending PUBREC (Mid: "+str(mid)+")")
        return self._encode_command_with_mid(PUBREC, mid, False)

    def encode_pubrel(self, mid, dup=False):
        self._easy_log(MQTT_LOG_DEBUG, "Sending PUBREL (Mid: "+str(mid)+")")
        return self._encode_command_with_mid(PUBREL|2, mid, dup)

    def encode_connect(self, keepalive, clean_session):
        # if self._protocol == MQTTv31:
        #     protocol = PROTOCOL_NAMEv31
        #     proto_ver = 3
        # else:
        #     protocol = PROTOCOL_NAMEv311
        #     proto_ver = 4
        # remaining_length = 2+len(protocol) + 1+1+2 + 2+len(self._client_id)
        # connect_flags = 0
        # if clean_session:
        #     connect_flags = connect_flags | 0x02
        #
        # if self._will:
        #     if self._will_payload is not None:
        #         remaining_length = remaining_length + 2+len(self._will_topic) + 2+len(self._will_payload)
        #     else:
        #         remaining_length = remaining_length + 2+len(self._will_topic) + 2
        #
        #     connect_flags = connect_flags | 0x04 | ((self._will_qos&0x03) << 3) | ((self._will_retain&0x01) << 5)
        #
        # if self._username:
        #     remaining_length = remaining_length + 2+len(self._username)
        #     connect_flags = connect_flags | 0x80
        #     if self._password:
        #         connect_flags = connect_flags | 0x40
        #         remaining_length = remaining_length + 2+len(self._password)
        #
        # command = CONNECT
        # packet = bytearray()
        # packet.extend(struct.pack("!B", command))
        #
        # self._pack_remaining_length(packet, remaining_length)
        # packet.extend(struct.pack("!H"+str(len(protocol))+"sBBH", len(protocol), protocol, proto_ver, connect_flags, keepalive))
        #
        # self._pack_str16(packet, self._client_id)
        #
        # if self._will:
        #     self._pack_str16(packet, self._will_topic)
        #     if self._will_payload is None or len(self._will_payload) == 0:
        #         packet.extend(struct.pack("!H", 0))
        #     else:
        #         self._pack_str16(packet, self._will_payload)
        #
        # if self._username:
        #     self._pack_str16(packet, self._username)
        #
        #     if self._password:
        #         self._pack_str16(packet, self._password)
        #
        # self._keepalive = keepalive
        # return self._packet_queue(command, packet, 0, 0)
        pass # TODO - Implement encoding CONNECT later, first we are focusing on the server's needs

    def encode_connack(self, connack_result_code):
        return self._encode_command_with_mid(CONNACK, connack_result_code, 0)

    def encode_disconnect(self):
        return self._encode_simple_command(DISCONNECT)

    def encode_pingreq(self):
        return self._encode_simple_command(PINGREQ)

    def encode_pingresp(self):
        return self._encode_simple_command(PINGRESP)

    def encode_puback(self, mid):
        return self._encode_command_with_mid(PUBACK, mid, False)

    def encode_pubcomp(self, mid):
        return self._encode_command_with_mid(PUBCOMP, mid, False)

    def encode_subscribe(self, dup, topics):
        # remaining_length = 2
        # for t in topics:
        #     remaining_length = remaining_length + 2+len(t[0])+1
        #
        # command = SUBSCRIBE | (dup<<3) | (1<<1)
        # packet = bytearray()
        # packet.extend(struct.pack("!B", command))
        # self._pack_remaining_length(packet, remaining_length)
        # local_mid = self._mid_generate()
        # packet.extend(struct.pack("!H", local_mid))
        # for t in topics:
        #     self._pack_str16(packet, t[0])
        #     packet.extend(struct.pack("B", t[1]))
        # return (self._packet_queue(command, packet, local_mid, 1), local_mid)
        pass ## TODO - Implement encoding SUBSCRIBE later, first we are focusing on the server's needs

    def encode_suback(self, mid, topics_and_qos):
        remaining_length = 2
        for t in topics_and_qos:
            remaining_length += 1

        command = SUBACK
        packet = bytearray()
        packet.extend(struct.pack("!B", command))
        self._pack_remaining_length(packet, remaining_length)
        local_mid = mid
        packet.extend(struct.pack("!H", local_mid))
        for t in topics_and_qos:
            packet.extend(struct.pack("B", t[1]))
        return (self.on_packet_encoded(command, packet, local_mid, 1), local_mid)

    def encode_unsubscribe(self, dup, topics):
        #     remaining_length = 2
        #     for t in topics:
        #         remaining_length = remaining_length + 2+len(t)
        #
        #     command = UNSUBSCRIBE | (dup<<3) | (1<<1)
        #     packet = bytearray()
        #     packet.extend(struct.pack("!B", command))
        #     self._pack_remaining_length(packet, remaining_length)
        #     local_mid = self._mid_generate()
        #     packet.extend(struct.pack("!H", local_mid))
        #     for t in topics:
        #         self._pack_str16(packet, t)
        #     return (self._packet_queue(command, packet, local_mid, 1), local_mid)
        pass # TODO - Implement encoding UNSUBSCRIBE later, first we are focusing on the server's needs

    def encode_unsuback(self, mid):
        return self._encode_command_with_mid(UNSUBACK, mid)


    # ============================================================
    # Private functions
    # ============================================================

    def _encode_command_with_mid(self, command, mid, dup):
        # For PUBACK, PUBCOMP, PUBREC, PUBREL and UNSUBACK
        if dup:
            command = command | 8

        remaining_length = 2
        packet = struct.pack('!BBH', command, remaining_length, mid)
        return self.on_packet_encoded(command, packet, mid, 1)

    def _encode_simple_command(self, command):
        # For DISCONNECT, PINGREQ and PINGRESP
        remaining_length = 0
        packet = struct.pack('!BB', command, remaining_length)
        return self.on_packet_encoded(command, packet, 0, 0)

    def _easy_log(self, level, buf):
        if self.on_log:
            self.on_log(self, self._userdata, level, buf)

    def _pack_remaining_length(self, packet, remaining_length):
        remaining_bytes = []
        while True:
            byte = remaining_length % 128
            remaining_length = remaining_length // 128
            # If there are more digits to encode, set the top bit of this digit
            if remaining_length > 0:
                byte = byte | 0x80

            remaining_bytes.append(byte)
            packet.extend(struct.pack("!B", byte))
            if remaining_length == 0:
                # FIXME - this doesn't deal with incorrectly large payloads
                return packet

    def _pack_str16(self, packet, data):
        if sys.version_info[0] < 3:
            if isinstance(data, bytearray):
                packet.extend(struct.pack("!H", len(data)))
                packet.extend(data)
            elif isinstance(data, str):
                udata = data.encode('utf-8')
                pack_format = "!H" + str(len(udata)) + "s"
                packet.extend(struct.pack(pack_format, len(udata), udata))
            elif isinstance(data, unicode):
                udata = data.encode('utf-8')
                pack_format = "!H" + str(len(udata)) + "s"
                packet.extend(struct.pack(pack_format, len(udata), udata))
            else:
                raise TypeError
        else:
            if isinstance(data, bytearray) or isinstance(data, bytes):
                packet.extend(struct.pack("!H", len(data)))
                packet.extend(data)
            elif isinstance(data, str):
                udata = data.encode('utf-8')
                pack_format = "!H" + str(len(udata)) + "s"
                packet.extend(struct.pack(pack_format, len(udata), udata))
            else:
                raise TypeError

    @staticmethod
    def decode_subscribe_packet(subscribe_packet, remaining_length):
        topics_and_qos = []
        position = 2
        pack_format = "!H" + str((remaining_length-2)) + 's'
        (mid, rest) = struct.unpack(pack_format, subscribe_packet)

        while position < remaining_length:
            position += 2
            pack_format = "!H" + str(len(rest) - 2) + 's'
            (topic_length, rest) = struct.unpack(pack_format, rest)
            position += topic_length + 1
            pack_format = str(topic_length) + 's' + 'B'

            if remaining_length > position:
                pack_format += str(remaining_length - position) + 's'
                (topic_name, qos, rest) = struct.unpack(pack_format, rest)
            else:
                (topic_name, qos) = struct.unpack(pack_format, rest)
                rest = None
            topics_and_qos.append((topic_name, qos))

        return mid, topics_and_qos

    @staticmethod
    def decode_unsubscribe_packet(unsubscribe_packet, remaining_length):
        topics = []
        position = 2
        pack_format = "!H" + str((remaining_length-2)) + 's'
        (mid, rest) = struct.unpack(pack_format, unsubscribe_packet)

        while position < remaining_length:
            position += 2
            pack_format = "!H" + str(len(rest) - 2) + 's'
            (topic_length, rest) = struct.unpack(pack_format, rest)
            position += topic_length
            pack_format = str(topic_length) + 's'

            if remaining_length > position:
                pack_format += str(remaining_length - position) + 's'
                (topic_name, rest) = struct.unpack(pack_format, rest)
            else:
                (topic_name, rest) = struct.unpack(pack_format, rest)
                rest = None
            topics.append(topic_name)

        return mid, topics
