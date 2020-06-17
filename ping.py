# coding: utf-8

# Cannot find a nice implementation of pinging in Python so I'm creating my own

import struct
import socket
import random
import time
import select

ICMP_STRUCTURE_FMT = "<BBHHH"  # Network is big-endian but idk why "!" didn't work :/
ICMP_ECHO_REQUEST = 8
ICMP_CODE = socket.getprotobyname('icmp')


class Response:
    def __init__(self):
        self.ret_code = 1
        self.type = 0
        self.code = 0
        self.checksum = 0
        self.id = 0
        self.sequence = 0


class ICMPPacket:
    def __init__(self,
                 icmp_type=ICMP_ECHO_REQUEST,
                 icmp_code=0,
                 icmp_chks=0,
                 icmp_id=1,
                 icmp_sequence=1,
                 data=''):
        self.icmp_type = icmp_type
        self.icmp_code = icmp_code
        self.icmp_chks = icmp_chks
        self.icmp_id = icmp_id
        self.icmp_sequence = icmp_sequence
        self.data = data
        self.raw = None
        self.create_icmp_field()

    def create_icmp_field(self):
        # We have to calculate the raw first, assume that the checksum field
        # is all zeros.
        self.raw = struct.pack(ICMP_STRUCTURE_FMT,
                               self.icmp_type,
                               self.icmp_code,
                               self.icmp_chks,
                               self.icmp_id,
                               self.icmp_sequence)

        # Calculate the real checksum and pack it again.
        self.icmp_chks = self.chksum(self.raw + bytes(self.data.encode('ascii')))
        self.raw = struct.pack(ICMP_STRUCTURE_FMT,
                               self.icmp_type,
                               self.icmp_code,
                               self.icmp_chks,
                               self.icmp_id,
                               self.icmp_sequence)
        return

    def chksum(self, msg):
        s = 0

        for i in range(0, len(msg), 2):
            a = msg[i]
            b = msg[i+1]
            s = s + (a + (b << 8))

        s = s + (s >> 16)
        s = ~s & 0xffff

        return s


def extract_icmp_header(data):
    icmp_header = struct.unpack(ICMP_STRUCTURE_FMT, data)
    data = {
        'type':     icmp_header[0],
        'code':     icmp_header[1],
        'checksum': icmp_header[2],
        'id':       icmp_header[3],
        'seq':      icmp_header[4]
    }
    return data


def send_one_request(s, addr=None):
    packet_id = random.randrange(10000, 65000)
    packet = ICMPPacket(icmp_id=packet_id).raw

    while packet:
        sent = s.sendto(packet, (addr, 1))  # Port number is not necessary
        packet = packet[sent:]

    return packet_id


def catch_reply(s, ID, time_sent, timeout=1):
    while True:
        starting_time = time.time()

        process = select.select([s], [], [], timeout)
        if process[0] == []:
            return None

        # Extracting received message
        rec_packet, addr = s.recvfrom(1024)
        icmp = rec_packet[20:28]
        _id = extract_icmp_header(icmp)["id"]
        if _id == ID:
            return extract_icmp_header(icmp)
    return None


def ping(addr, timeout=1):
    """Ping a host and get response as an object"""
    s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    ID = send_one_request(s, addr=addr)

    reply = catch_reply(s, ID, time.time(), timeout=timeout)
    response = Response()

    if reply is not None:
        response.ret_code = 0
        response.type = reply['type']
        response.code = reply['code']
        response.checksum = reply['checksum']
        response.id = reply['id']
        response.sequence = reply['seq']
    else:
        response.ret_code = 1
    s.close()
    return response
