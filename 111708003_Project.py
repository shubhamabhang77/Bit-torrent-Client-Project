#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Single Files
 {
     'announce': 'http://bttracker.debian.org:6969/announce',
     'info':
     {
         'name': 'debian-503-amd64-CD-1.iso',
         'piece length': 262144,
         'length': 678301696,
         'pieces': <binary SHA1 hashes>
     }
 }




Multiple Files
{
     'announce': 'http://tracker.site1.com/announce',
     'info':
     {
         'name': 'directoryName',
         'piece length': 262144,
         'files':
         [
             {'path': ['111.txt'], 'length': 111},
             {'path': ['222.txt'], 'length': 222}
         ],
         'pieces': <binary SHA1 hashes>
     }
 }
"""

import bencode 
import re
import sys, os
import socket
import tqdm
import random
import struct
import hashlib
import binascii
import urllib.request
import urllib.parse 
import traceback
import threading
import requests

peer_id = b'-SAshubhamabhang777-'
port = 6880



#to read torrent file
def read(filename):
    fd = open(filename, 'rb')
    raw_data = fd.read()
    torrent_data = bencode.decode(raw_data)
    return torrent_data


#to get announce list
def announce_list(torrent_data):
    try:
        temp = torrent_data['announce-list']
        return temp
    except:
        return torrent_data['announce']

#to get the data like ip_address, port_number and protocol name of tracker
def tracker_data(announce):
    raw = re.split(':|//|/', announce)
    protocol = raw[0]
    tracker_ip = raw[2]
    tracker_port = raw[3]
    socket.setdefaulttimeout(0.1)
    try:
        tracker_ip = socket.getaddrinfo(tracker_ip, None)[0][4][0]
    except:
        return 'error'
    else:
        return protocol, tracker_ip, tracker_port

    
#to get the random trascation id
def get_transcation_id():
    return random.randrange(1,65535)


#to pack the connect request
def pack_connect_request(protocol_id, action, transcation_id):
    return struct.pack(">QLL", protocol_id, action, transcation_id)


#to unpack the connect response
def unpack_connect_response(packet):
    return struct.unpack(">LLQ", packet)


#to pack scrape request
def pack_scrape_request(connection_id, action, transcation_id, info_hash):
    packet_hashes = str()
    packet_hashes = bytearray(packet_hashes, 'utf-8') + binascii.unhexlify(info_hash)
    return struct.pack(">QLL", connection_id, action, transcation_id) + packet_hashes


#to unpack scrape response
def unpack_scrape_response(packet):
    return struct.unpack(">LLLLL", packet)


def pack_announce_request(connection_id, action, transcation_id, info_hash, peer_id, downloaded, left, uploaded, event, ip, key, num_want, port):
    packet_hashes = str()
    packet_hashes = bytearray(packet_hashes, 'utf-8') + binascii.unhexlify(info_hash)
    return struct.pack(">QLL", connection_id, action, transcation_id) + packet_hashes + struct.pack(">20sQQQLLLLH", peer_id, downloaded, left, uploaded, event, ip, key, num_want, port)


def unpack_announce_response(packet, num_want):   
    peer_ids = []
    for i in range(num_want):
        temp = struct.unpack_from("!BBBBH", packet, 20 + (i*6))
        ip = '.'.join((str(temp[0]), str(temp[1]), str(temp[2]), str(temp[3])))
        peer_ids.append((ip , temp[4]))
    return peer_ids


#to get list of working trackers
def get_working_trackers(trackers_list):
    list_of_working_trackers = []
    for i in trackers_list:
        if tracker_data(i) == 'error':
            pass
        else:
            protocol, ip, port = tracker_data(i)
            temp = [protocol, ip, port]
            list_of_working_trackers.append(temp)
    return list_of_working_trackers


#to get info_hash of torrent
def get_info_hash(torrent_data):
    return hashlib.sha1(bencode.bencode(torrent_data['info'])).hexdigest()


# to get no. of pieces
def get_piece_count(torrent_data, file_size):
    temp = file_size / torrent_data['info']['piece length']
    if temp > int(temp):
        temp = int(temp) + 1
    return temp


#to get size of torrent file
def get_file_size(torrent_data):
    try:
        file_size = 0
        for i in torrent_data['info']['files']:
            file_size = file_size + i['length']
        return file_size
    except:
        return torrent_data['info']['length']
        
#to make a connection request and returns connection id
def make_connect(server_name, server_port):
    protocol_id = 0x41727101980
    action = 0
    transcation_id = get_transcation_id()
    request_packet = pack_connect_request(protocol_id, action, transcation_id)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(10)
    client_socket.connect((server_name, server_port))
    client_socket.send(request_packet)
    client_socket.settimeout(4.00)
    try:
        packet = client_socket.recv(16)
    except:
        return 'connection_timeout'
    else:

        packet = unpack_connect_response(packet) 
    
        if transcation_id != packet[1]:
            raise RuntimeError("Trascation_id doesn't Match!!\n")
        if packet[0] == 0x3:
            raise RuntimeError("Some error occured during connection!!\n")
            
        connection_id = packet[2]
        return connection_id
    
    
#to make a scrape request which returns a tuple of seeders, completed and leechers
def make_scrape(server_name, server_port, info_hash):
    connection_id = make_connect(server_name, server_port)
    if connection_id == 'connection_timeout':
        return 'connection_timeout'
    action = 2
    transcation_id = get_transcation_id()
    
    scrape_req_packet = pack_scrape_request(connection_id, action, transcation_id, info_hash)
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    client_socket.connect((server_name, server_port))
    client_socket.send(scrape_req_packet)
    client_socket.settimeout(4.00)
    try:
        packet= client_socket.recv(20)
    except:
        return 'scrape_timeout'
    else:
        packet = unpack_scrape_response(packet)

    
        if transcation_id != packet[1]:
            raise RuntimeError("Trascation_id doesn't Match!!\n")
            if action == 0x3:
                raise RuntimeError("Some error occured during connection!!\n")
                
                seeders = packet[2]
                completed = packet[3]
                leechers = packet[4]
                temp = (seeders, completed, leechers)
                return temp   
        
    
    
#to make announcement request which returns list of peers
def make_announce(server_name, server_port, info_hash, file_size):
    connection_id = make_connect(server_name, server_port)
    if connection_id == 'connection_timeout':
        return 'connection_timeout'
    
    action = 1
    transcation_id = get_transcation_id()
    downloaded = 0
    left = file_size
    uploaded = 0
    event = 2
    IP_address = 0
    key = 0
    num_want = 50
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #while True:
    #    try:
    #        client_socket.bind(('', port))
    #        break
    #    except:
    #        port = port + 1
    
    announce_req_packet = pack_announce_request(connection_id, action, transcation_id, info_hash, peer_id, downloaded, left, uploaded, event, IP_address, key, num_want, port)
    client_socket.settimeout(10)
    client_socket.connect((server_name, server_port))
    client_socket.send(announce_req_packet)
    client_socket.settimeout(4.00)
    try:
        packet = client_socket.recv(20 + num_want*6)
    except:
        return 'announce_timeout'
    else:
        peer_ids = unpack_announce_response(packet, num_want)
        client_socket.shutdown(1)
        client_socket.close()
        return peer_ids



def udp_connection(tracker, info_hash, file_size):
    servername = tracker[1]
    serverport = int(tracker[2])
    peer_ids = make_announce(servername, serverport, info_hash, file_size)
    return peer_ids


def http_connection(tracker, info_hash, file_size):
    tracker = 'http://' + tracker[1] + ':' + tracker[2] + '/announce'

    downloaded = 0
    uploaded = 0
    event = 'started'

    info_hash = binascii.unhexlify(info_hash)


    
    argu = {
         'info_hash': info_hash,
         'peer_id': peer_id,
         'port': port,
         'uploaded': uploaded,
         'downloaded': downloaded,
         'left': file_size,
         'event': event,
         'compact': 1
    }
    
    url = "{}?{}".format(tracker, urllib.parse.urlencode(argu))
    try:
        response_packet = urllib.request.urlopen(url, timeout=10)
    except:
        return 'timed_out'
    response_packet = response_packet.read()
    index = str(response_packet).find('peers')
    
    temp = str(response_packet)[index+5:-1]
    temp = temp.split(':')
    
    peer_ids = []
    for i in range(int(int(temp[0])/6)):
        s = struct.unpack_from("!BBBBH", response_packet[index+4+len(temp[0]):], i*6)
        ip = '.'.join((str(s[0]), str(s[1]), str(s[2]), str(s[3])))
        peer_ids.append((ip , s[4]))


    #client_socket.shutdown(1)
    #client_socket.close()
    return peer_ids


def make_handshake_mes(torrent_data):
    packet_peer_id = peer_id
    info_hash = get_info_hash(torrent_data)
    packet_hashes = str()
    packet_hashes = bytearray(packet_hashes, 'utf-8') + binascii.unhexlify(info_hash)
    
    pstr = 'BitTorrent protocol'
    pstr_by = bytes(pstr, 'utf-8')

    handshake = chr(19).encode() + pstr_by + (chr(0) * 8).encode() + packet_hashes + packet_peer_id
    return handshake



def downloading(handshake, peer_ip, peer_port, pieces_data, start, end, block_count):
    blocks_data = []
    try:
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        clientSocket.settimeout(10.0)
        clientSocket.connect((peer_ip, peer_port))
        clientSocket.send(handshake)
        
        clientSocket.settimeout(10)
        data = clientSocket.recv(4096)
        clientSocket.settimeout(10)    
        data += clientSocket.recv(4096)
        d = struct.unpack('!LB', data[-5:])
    except:
        return


    if d[0] == 1 and d[1] == 1:
        pass
    else:
        #interested
        length_prefix = 1
        message_id = 2
        packet = struct.pack('!LB', length_prefix, message_id)
        try:
            clientSocket.send(packet)
            clientSocket.settimeout(5)
            d = clientSocket.recv(5)
        except:
            return
        if len(d) != 0:
            d = struct.unpack('!LB', d)
        else:
            return


    if d[0] == 1 and d[1] == 1:
        
        if (len(pieces_data)-1) == start:
            blocks_data = []
            if pieces_data[start][3] == 'NO':
                whole = b''
                total = 0
                block_count = pieces_data[start][5] / 16384
                
                if block_count > int(block_count):
                    block_count = int(block_count) + 1
                else:
                    block_count = int(block_count)

                for i in range(int(block_count)):
                    pi = b''
                    length_prefix = 13
                    message_id = 6
                    index = start
                    begin = i
                    length = 2**14
                    packet = struct.pack('!LBLLL', length_prefix, message_id, index, begin, length)                
                    clientSocket.send(packet)
                
                
                for w in range(block_count):
                    blocks_data.append([start, w, b''])
                    
                while True:
                    temp = b''
                    try: 
                        temp = clientSocket.recv(2**19)
                    except:
                        #traceback.print_exc()
                        pass
                    whole = whole + temp
                    if len(temp) == 0:
                        break
                
                
                q = len(whole) % (pieces_data[start][5] + 13*block_count)
                
                t1 = -1
                for l in range(q):
                    if struct.unpack_from('!B', whole, l)[0] == 0:
                        t1 = l
                        pass
                    else:
                        break
                if t1 == (q-1):
                    whole = whole[q:]
                else:
                    whole = whole[:(-1*q)]
                    
                    

                pieces_data[start][4] = b''
                
                for i in range(block_count):
                    try:
                        s = struct.unpack("!LBLL", whole[:13])
                    except:
                        break
                    else:
                        if i == (block_count-1):
                            blocks_data[s[3]][2] += (whole[13:])
                            break
                        blocks_data[s[3]][2] += (whole[13:16397])
                            #shubham.write(whole[13:16397])
                            # break
                        whole = whole[16397:]



                blocks_data = sorted(blocks_data, key = lambda x: x[1])
                
                
                for r in range(len(blocks_data)):
                    pieces_data[start][4] += blocks_data[r][2]
                
                
                if s[2] == start and len(pieces_data[start][4]) == pieces_data[start][5]:
                    pieces_data[start][3] = 'YES'
                    
                
                
        for j in range(start, end):
            blocks_data = []
            if pieces_data[j][3] == 'NO':
                whole = b''
                total = 0
            
            
                for w in range(block_count):
                    blocks_data.append([start, w, b''])

                
                for i in range(int(block_count)):
                    pi = b''
                    length_prefix = 13
                    message_id = 6
                    index = j
                    begin = i
                    length = 2**14
                    packet = struct.pack('!LBLLL', length_prefix, message_id, index, begin, length)                
                    clientSocket.send(packet)
                
                x = block_count*16397
                while True and len(whole) < x:
                    temp = b''
                    try: 
                        temp = clientSocket.recv(2**19)
                    except:
                        #traceback.print_exc()
                        pass
                    whole = whole + temp
                    if len(temp) == 0:
                        break
                



                q = len(whole) % 16397 
                t1 = -1
                for l in range(q):
                    if struct.unpack_from('!B', whole, l)[0] == 0:
                        t1 = l
                        pass
                    else:
                        return
                if t1 == (q-1):
                    whole = whole[q:]
                else:
                    whole = whole[:(-1*q)]
                
                
                
                pieces_data[j][4] = b''
                 
                for i in range(block_count):
                    try:
                        s = struct.unpack("!LBLL", whole[:13])
                    except:
                        return
                    else:
                        blocks_data[s[3]][2] += (whole[13:16397])
                        whole = whole[16397:]

                blocks_data = sorted(blocks_data, key = lambda x: x[1])
                
                for r in range(len(blocks_data)):
                    pieces_data[j][4] += blocks_data[r][2]
                                
                if s[2] == j and len(pieces_data[j][4]) == block_count*16384:
                    pieces_data[j][3] = 'YES'
   


def uplaoding(peer_ip, peer_port, piece_no):
    pass

def seq_data_wri(pieces_data, destfilename, block_count):
    size = block_count * 16384
    i = 0
    for i in (range(len(pieces_data)-1)):
        while True:
            if pieces_data[i][3] == 'YES' and len(pieces_data[i][4]) == size:
                destfilename.write(pieces_data[i][4])
                pieces_data[i][4] = b''
                break
            
    if i == len(pieces_data)-1 :
        if pieces_data[i+1][3] == 'YES':
            destfilename.write(pieces_data[i][4])
            pieces_data[i][4] = b''
                


def handshaking(client_socket, pieces_data, handshaking_peers, peer_ip, peer_port, handshake_msg, packet_hashes):
    i = (peer_ip, peer_port)
    try:
        client_socket.send(handshake_msg)
        
        data = b''
        data1 = b''
        temp = b''
        client_socket.settimeout(10)
        data = client_socket.recv(68)
        client_socket.settimeout(10)
        temp = client_socket.recv(4096)
        data1 = data1 + temp
        client_socket.settimeout(10)
        temp = client_socket.recv(4096)
        data1 += temp        

        if len(data) > 67:
            temp = struct.unpack_from("!B19s8x20s20s", data, 0)
            if temp[2] != bytes(packet_hashes):
                pass
            else:
                print('connection established with ', peer_ip, peer_port, ' handshake received ', len(data1))
                handshaking_peers.append(i)
                index = 0
                while True:
                    try:
                        length_prefix = struct.unpack_from('!L', data1, index)
                    except:
                        break
                    length_prefix = length_prefix[0]
                    index = index + 4
                    
                    if(length_prefix == 0):
                        continue
                    
                    message_id = struct.unpack_from('!B', data1, index)
                    message_id = message_id[0]
                    index = index + 1
                    
                    
                    if (length_prefix == 1) and (message_id == 0):
                        choke = 1# that is choked
                        pass
                    
                    elif (length_prefix == 1) and (message_id == 1):
                        choke = 0 # that is unchoked
                        pass
                    
                    
                    elif (length_prefix == 1) and (message_id == 2):
                        interested = 1 # that is interested
                        pass
                    
                    
                    elif (length_prefix == 1) and (message_id == 3):
                        interested = 0 # that is not interested
                        pass
                    
                    
                    elif (length_prefix == 1) and (message_id == 14):
                        for z in range(piece_count):
                            pieces_data[z][1] += 1
                            pieces_data[z][2].append(i)
                        break
                        pass
                    
                    
                    elif (length_prefix == 1) and (message_id == 15):
                        break
                        pass
                    
                    
                    elif (length_prefix == 5) and (message_id == 4):
                        z = struct.unpack_from('!L', data1, index)
                        z = z[0]
                        index = index + 4
                        pieces_data[z][1] += 1
                        pieces_data[z][2].append(i)
                        pass
                    
                    
                    elif (message_id == 5):
                        bitfield = b''
                        bitfield = data1[index:index+length_prefix-1]
                        index = index + length_prefix - 1
                        z = 0
                        for k in range(len(bitfield)):
                            gaon = "{0:b}".format(bitfield[k])
                            a = len(gaon)
                            z = z + (8-a)
                            for q in range(a):
                                if gaon[q] == '1':
                                    pieces_data[z][1] = pieces_data[z][1] + 1
                                    pieces_data[z][2].append(i)
                                z += 1         
                                
                    elif (length_prefix == 13) and (message_id == 6):
                        m = struct.unpack_from('!LLL', data1, index)
                        index += 12
                        pass
                    
                    
                    elif (message_id == 7):
                        recv_piece = data1[index: index+length_prefix-9]
                        index = index + length_prefix - 9
                        pass
                    
                    elif (length_prefix == 13) and (message_id == 8):
                        v = struct.unpack_from('!LLL', data1, index)
                        index += 12
                        pass
                    
                    elif(length_prefix == 3) and (message_id == 9):
                        recv_port = struct.unpack('!L', data1, index)
                        index += 4
                        recv_port = recv_port[0]
                        pass
                    
    except:
        pass

    return pieces_data
    

def progress_bar(torrent_data):
    i = 0
    count = 0
    while   count != len(torrent_data):
        count = 0
        for i in range(len(torrent_data)):
            if torrent_data[i][3] == 'YES':
                count += 1
        

def main():
    try:
        filename = sys.argv[1]
    except:
        print('Usage: ./filename.py  torrent_filename')
        return 
    else:
        
        
        #filename = '/home/shubham/Nawp_Project/fast.torrent'
        
        torrent_data = read(filename)


            
        trackers = announce_list(torrent_data)
        
        info_hash = get_info_hash(torrent_data)
        file_size = get_file_size(torrent_data)
        piece_size = torrent_data['info']['piece length']
        packet_hashes = str()
        packet_hashes = bytearray(packet_hashes, 'utf-8') + binascii.unhexlify(info_hash)
        
        piece_count = get_piece_count(torrent_data, file_size)
        
        block_count = int(torrent_data['info']['piece length']/2**14)
        
        
        
        
        pwd = os.getcwd()
        try:
            torrent_data['info']['files']
        except KeyError:
            try:
                sys.argv[2]
            except:
                file = pwd + '/' + torrent_data['info']['name']
            else:
                file = pwd + '/' + sys.argv[2] + '/' + file
            shubham = open(file, 'wb+')
            print('File_Name: ', torrent_data['info']['name'], '\nFile_size: ', torrent_data['info']['length'], 'bytes')
        else:
            print('Directory_Name: ', torrent_data['info']['name'])
            for i in range(len(torrent_data['info']['files'][0])):
                print('File_Name: ', torrent_data['info']['files'][i]['path'][0], '\nFile_size: ', torrent_data['info']['files'][i]['length'], 'bytes')
            shubham = open('temporary', 'wb+')

        print('Info_hash: ', info_hash)
        print('No. of Pieces: ', piece_count)
        print('Piece Size: ', piece_size, 'bytes\n')
        
        
        if type(trackers) == list:
            trackers_list = []
            for i in trackers:
                for j in i:
                    trackers_list.append(j)
        else:
            trackers_list = [trackers]
            
        
        list_of_working_tracker =  get_working_trackers(trackers_list)
        
        total_peers = []
        for tracker in list_of_working_tracker:
            if tracker[0] == 'udp':
                try:
                    peer_ids = udp_connection(tracker, info_hash, file_size)
                    if peer_ids == 'announce_timeout' or peer_ids == 'connection_timeout' or peer_ids == 'scrape_timeout':
                        print('timed_out: poor network connection', peer_ids)
                        continue
                    total_peers = total_peers + peer_ids
                except:
                    pass
            elif tracker[0] == 'http':
                try:
                    peer_ids = http_connection(tracker, info_hash, file_size)
                    if peer_ids == 'timed_out':
                        print('timed_out: poor network connection')
                        continue
                    total_peers = total_peers + peer_ids
        
                except:
                    pass
        
        
        print("Got", len(total_peers), "peers from all trackers", total_peers, '\n')
        handshake_msg = make_handshake_mes(torrent_data)
        last_piece_size = file_size % piece_size
        pieces_data = []
        for i in range(piece_count):
            peers = []
            count = 0
            no = i
            temp = [no, count, peers, 'NO', b'']
            if i == (piece_count-1):
                temp.append(last_piece_size)
            pieces_data.append(temp)
        last_piece = len(pieces_data)-1
        
        

        handshaking_peers = []
        if len(total_peers) < 25:
            timeout = 2
        else:
            timeout = 1
        for i in total_peers:
            try:
                clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                clientSocket.settimeout(timeout)
                clientSocket.connect((i[0], i[1]))
                
                pieces_data = handshaking(clientSocket, pieces_data, handshaking_peers, i[0], i[1], handshake_msg, packet_hashes)


                clientSocket.close()
            except:
                pass
            
            
        
        print('handshaked with ', len(handshaking_peers))
        print(handshaking_peers)
        
        
        if len(handshaking_peers) == 0:
            print('No Peers are sending handshake')
            return
        
        

        start = 0
        end = 0
        

        
        loop_running = int(piece_count / (len(handshaking_peers) * 2))
        last_loop = piece_count - len(handshaking_peers) * 2 * loop_running

        stor_thread = threading.Thread(target = seq_data_wri, args=(pieces_data, shubham, block_count))
        stor_thread.start()
        
        for z in range(loop_running):
            threads = []
            print('hello')
            for e in range(len(handshaking_peers)):
                start = e * 2 + z * 2 * len(handshaking_peers)
                end = e * 2 + 2 + z * 2 * len(handshaking_peers)
                try:
                    pieces_data[start][2].index(handshaking_peers[e])
                    pieces_data[start+1][2].index(handshaking_peers[e])
                except:
                    print('da')
                    pass
                else:
                    print('downloading ', start, ' to ', end-1)
                    t1 = threading.Thread(target = downloading, args = (handshake_msg, handshaking_peers[e][0], handshaking_peers[e][1], pieces_data, start, end, block_count))
                    threads.append(t1)
                    t1.start()
            for thread in threads:
                thread.join()
            for y in range(z * len(handshaking_peers) * 2, z * 2 * len(handshaking_peers) + 2 * len(handshaking_peers)):
                if pieces_data[y][3] == 'NO':
                    while pieces_data[y][3] == 'NO':
                        for y1 in range(len(handshaking_peers)):
                            if pieces_data[y][3] == 'NO':
                                try:
                                    pieces_data[y][2].index(handshaking_peers[y1])
                
                                    t6 = threading.Thread(target = downloading, args = (handshake_msg, handshaking_peers[y1][0], handshaking_peers[y1][1], pieces_data, y, y+1, block_count))
                                    
                                    t6.start()
                                    
                                    t6.join()
                                except:
                                    pass
        
        for k in range(piece_count-last_loop, piece_count):
            if pieces_data[k][3] == 'NO':
                while pieces_data[k][3] == 'NO':
                    for y1 in range(len(handshaking_peers)):
                        if pieces_data[k][3] == 'NO':
                            try:
                                pieces_data[k][2].index(handshaking_peers[y1])
                                t6 = threading.Thread(target = downloading, args = (handshake_msg, handshaking_peers[y1][0], handshaking_peers[y1][1], pieces_data, k, k+1, block_count))
                                
                                t6.start()
                                
                                t6.join()
                                print('done ', k)
                            except:
                                pass

        stor_thread.join()
        shubham.close()
        
        try:
            torrent_data['info']['files']
        except:
            pass
        else:
            shubham = open('temporary', 'rb')
            for i in range(len(torrent_data['info']['files'])):
                file1 = open(torrent_data['info']['files'][i]['path'], 'wb+')
                file1.write(shubham.read(torrent_data['info']['files'][i]['length']))
                file1.close()


        
if __name__ == '__main__':
  main()
        
        