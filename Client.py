import socket
import sys
import string
import time
import copy
import bitarray
import os
import Constants
import MyHeader
import heapq
import threading
import base64
import shutil

'''
The client class is responsible for starting the communication with the server.
'''


class Client:
    '''
    The initialize method just initializes different variables that are being used throughout the communication.
    '''

    def __init__(self, ip, port, serverIP, serverPort):
        self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ip = ip
        self.port = port
        self.serverIP = serverIP
        self.serverPort = serverPort
        self.last_sent_packet = None
        self.connected = False
        self.active_communication = False
        self.fragment_size = Constants.max_fragment_size * 8
        self.fragments_sent = []
        self.prev_seq_num = 0
        self.next_fragment = 0
        self.keep_alive=False
        self.assembled_message = b""
        self.fragmented_message = []
        self.name_of_file = None
        self.file_data = b""
        self.file = None
        self.path =os.path.abspath(os.getcwd())
        self.last = None
        self.receive_Thread = None
        self.menu_Thread = None
        self.end_received = None
        self.transfer_in_progress = -1
        self.problem_send = 200
        self.crntpacket = None
        self.packet_counter = 0
        self.end_received = 0
        self.resend_in_prog = 0
        self.receiving_in_progress = False
        self.fragments = []
        heapq.heapify(self.fragments)
        self.ra_recieved = True
        self.start()

    '''
    This method is responsible for sending the packet to the server, and also incrementing the sequence number.
    It is also here where corrupted packets can be simulated by the problem_send variable.
    '''

    def send_to_server(self, packet):
        if self.problem_send > -1 and self.packet_counter / self.problem_send == 1:

            self.last_sent_packet = packet
            self.prev_seq_num = packet.get_seq_num()
            self.packet_counter = self.packet_counter + 1
            pcopy = copy.deepcopy(packet)
            pcopy.set_Corrupted()
            print("Sending corrupted packet: ", pcopy.get_all_data())


            self.clientSocket.sendto(pcopy.get_packet(), (self.serverIP, self.serverPort))

            return

        self.last_sent_packet = packet
        self.prev_seq_num = packet.get_seq_num()
        #print("Sending packet: ",packet.get_all_data())
        self.clientSocket.sendto(packet.get_packet(), (self.serverIP, self.serverPort))
        self.packet_counter = self.packet_counter + 1

    '''
    This method is responsible for receiving the packets from the server
    it is set 576 because that is the most reliable byte amount.
    '''

    def receive_packet(self):
        packet, address = self.clientSocket.recvfrom(576)

        return packet

    '''
        This method is sets the servers ip adress and port.
    '''

    def setServer(self, serverIP, serverPort):
        self.serverIP = serverIP
        self.serverPort = serverPort

    '''
        This method is sets the clients ip adress and port and client socket.
        '''

    def setClient(self, ip, port):
        self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ip = ip
        self.port = port

    '''
        This method opens a file in binary mode.
        '''

    def open_file(self, name):
        self.file = open(name, "wb")

    '''
        This method creates a file in binary mode and append mode.
        '''

    def create_file(self, name):
        open(name, "w").close()
        self.file = open(name, "ab")

    '''
        This method writes to a file.
        '''

    def write_file(self, content):

        with self.file as file:
            file.write(content)
            file.close()

    '''
        This method reads a binary file.
        '''

    def read_file(self, path):
        with open(path, "rb") as file:
            return file.read()

    '''
        This method is responsible for sending a file to the server, based on the given file path of the file.
        Meanwhile the end-path must be also given, this is where the file will be saved after the file transfer.
        The way the method works is by first sending a non-fragmented file packet that will contain the path and the name of the file.
        Since this is a non-fragmented packet, means the data in it cannot be greater than the max_fragment_size.
        The client will keep sending this packet until it gets back an answer from the server. Then the client will start sending the fragmented file packets
        Meanwhile it will stop for every 100th packet sent, and will make sure the server sends back all the missing fragments so the client
        can resend them. After that both the server and the client will empty their memory so it doesn't get overloaded.
        The last fragment sent will contain and end flag, and will be resent until a server replies with an end acknowledgement.
        '''

    def send_file(self, filepath, filename,
                  destpath):

        try:
            file = self.read_file(filepath + filename)
        except Exception:
            print("Cannot find this file")
            return

        dest = destpath + filename
        namebits = bitarray.bitarray()
        namebits.frombytes(dest.encode('utf-8'))

        bits = bitarray.bitarray()
        bits.frombytes(file)
        lenght = len(bits)
        max_length = lenght
        name_size = len(namebits)
        packet_to_send = None
        print(name_size)

        if name_size <= Constants.file_name_size:
            if(name_size>self.fragment_size):
                dest = "1"

            self.transfer_in_progress = 2

            packet_to_send = MyHeader.make_nonfragmented_file_packet(dest.encode('utf-8'), self.prev_seq_num)
            self.end_received = False
            self.send_to_server(packet_to_send)

            while not self.end_received:
                self.send_to_server(packet_to_send)

                time.sleep(0.1)

        if self.transfer_in_progress != 2:

            self.transfer_in_progress = 4

            x = 0
            y = self.fragment_size
            z = 0
            self.resend_in_prog = 0
            percentage = 0
            while lenght > self.fragment_size:

                fragment = bits[x:y].tobytes()
                if z % Constants.memory_limit == 0 and z != 0:
                    self.resend_in_prog = 1

                packet_to_send = MyHeader.make_fragmented_file_packet(fragment, self.prev_seq_num, frag_num=z)
                z = z + 1
                x = x + self.fragment_size
                y = y + self.fragment_size
                self.fragments_sent.append(packet_to_send)
                print("Sending packet: ", packet_to_send.get_all_data())
                self.send_to_server(packet_to_send)
                lenght = lenght - self.fragment_size
                percentage += self.fragment_size
                print("* progress - ",round((percentage/max_length)*100,2), "%")
                u = 0
                while self.resend_in_prog == 1:
                    u = 1

                    self.send_to_server(packet_to_send)
                    time.sleep(0.1)
                while self.resend_in_prog == 2:
                    time.sleep(0.1)
                if u == 1:

                    self.fragments_sent.append(packet_to_send)

            fragment = bits[x:].tobytes()
            packet_to_send = MyHeader.make_end_file_packet(fragment, self.prev_seq_num, z)

            self.end_received = False
            print("Sending packet: ", packet_to_send.get_all_data())
            self.fragments_sent.append(packet_to_send
                                       )
            endloop = 0
            while not self.end_received:
                self.send_to_server(packet_to_send)
                endloop = endloop + 1
                if endloop == 20:
                    break
                time.sleep(0.1)

    '''
            This method is responsible for sending a message to the server.
            It can send out 2 types of packets, non-fragmented and fragmented.
            When sending non-fragmented packets it will stop for every 100th packet sent, and will make sure the server sends back all the missing fragments so the client
            can resend them. After that both the server and the client will empty their memory so it doesn't get overloaded.
            The last fragment sent will contain and end flag, and will be resent until a server replies with an end acknowledgement.
            '''

    def send_message(self, message):
        bits = bitarray.bitarray()
        bits.frombytes(message.encode('utf-8'))
        lenght = len(bits)


        strb = bitarray.bitarray()
        strb.frombytes(str.encode('utf-8'))


        packet_to_send = None

        if lenght <= self.fragment_size:
            self.transfer_in_progress = 1
            packet_to_send = MyHeader.make_nonfragmented_message_packet(message.encode('utf-8'), self.prev_seq_num)
            self.end_received = False

            self.send_to_server(packet_to_send)

            while not self.end_received:
                self.send_to_server(packet_to_send)

                time.sleep(0.1)


        else:

            self.transfer_in_progress = 3
            bits = bitarray.bitarray()
            bits.frombytes(message.encode('utf-8'))
            x = 0
            y = self.fragment_size
            z = 0
            self.resend_in_prog = 0
            while lenght > self.fragment_size:

                fragment = bits[x:y].tobytes()
                if z % Constants.memory_limit == 0 and z != 0:
                    self.resend_in_prog = 1

                packet_to_send = MyHeader.make_fragmented_message_packet(fragment, self.prev_seq_num, frag_num=z)
                z = z + 1

                x = x + self.fragment_size
                y = y + self.fragment_size
                self.send_to_server(packet_to_send)
                self.fragments_sent.append(packet_to_send)
                lenght = lenght - self.fragment_size

                u = 0
                while self.resend_in_prog == 1:
                    u = 1

                    self.send_to_server(packet_to_send)
                    time.sleep(0.1)
                while self.resend_in_prog == 2:
                    time.sleep(0.1)
                if u == 1:
                    self.fragments_sent.append(packet_to_send)

            fragment = bits[x:].tobytes()
            packet_to_send = MyHeader.make_end_message_packet(fragment, self.prev_seq_num, z)

            self.end_received = False
            self.fragments_sent.append(packet_to_send)
            endloop = 0
            while not self.end_received:
                self.send_to_server(packet_to_send)
                endloop = endloop + 1
                if endloop == 20:
                    break

                time.sleep(0.1)

    '''
    This is the start method where the different threads are initialized an run. Such as the menu, recieving packets and keeping up the connection with the server.
    '''

    def start(self):
        def run(self):
            threading.Thread(target=receive, args=(self,)).start()
            threading.Thread(target=connect, args=(self,)).start()
            threading.Thread(target=menu, args=(self,)).start()

            ## server

        '''
        This method is responsible for sending packets that contain the missing fragments for the file.
        The are 2 modes, one is when they client reaches the 100th packet, for memory saving .
        The other mode is when it got the packet containing the end flag.
        This method uses a heap for storing the fragments
            '''

        def resend_file(self, packet, mode=-1):
            if self.next_fragment == 0 and self.last == packet.get_packet():
                self.receive_Thread = None
                return
            if packet.is_it_right_crc():
                last_seg_num = 0
                varr = len(self.fragments)
                for i in range(varr):
                    curr = heapq.heappop(self.fragments)
                    while curr[1].get_frag_num() < packet.get_frag_num() and curr[
                        1].get_frag_num() >= self.next_fragment:
                        if curr[1].get_frag_num() == self.next_fragment:

                            self.file.write(curr[1].get_data())


                            last_seg_num = curr[1].get_seq_num()
                            self.next_fragment = self.next_fragment + 1


                        elif curr[1].get_frag_num() > self.next_fragment:
                            print("Requesting fragment :", self.next_fragment)
                            resend_pack = MyHeader.make_resend_request_file_packet(prev_seq_num=last_seg_num,
                                                                                   frag_num=self.next_fragment)
                            last = copy.deepcopy(self.next_fragment)
                            anm = 0

                            while True:
                                self.send_to_server(resend_pack)

                                while last == self.next_fragment:
                                    anm = anm + 1
                                    if anm == 10000:
                                        break

                                if last!=self.next_fragment:
                                    break
                                anm = 0

                            # self.next_fragment = self.next_fragment + 1
                            # print('NEXT FRAG = ', self.next_fragment)

                if mode == 1:
                    self.next_fragment = self.next_fragment + 1
                    self.file.write(packet.get_data())
                    self.ra_recieved = False
                    while not self.ra_recieved:
                        self.send_to_server(MyHeader.make_res_ack_file_packet(packet.get_seq_num()))
                        time.sleep(0.1)


                else:
                    self.send_to_server(MyHeader.make_ack_end_file_packet(packet.get_seq_num()))
                    self.file.write(packet.get_data())
                    self.file.close()
                    print("[*] File transfer successful")
                    print("Name of file: ", self.name_of_file)

                    print("Amount of fragments: ", self.next_fragment + 1, "\nAmount of bytes:",
                          os.path.getsize(self.name_of_file))
                    print("The file can be found in: ", self.path)
                    try:
                        os.remove(self.path+self.name_of_file)
                    except:
                        print(".")
                    try:
                        shutil.move(self.name_of_file, self.path)
                    except:
                        print("")



                    self.next_fragment = 0
                    self.last = packet.get_packet()


                    self.receiving_in_progress = False

                self.receive_Thread = None

        '''
                This method is responsible for sending packets that contain the missing fragments for the message.
                The are 2 modes, one is when they client reaches the 100th packet, for memory saving .
                The other mode is when it got the packet containing the end flag.
                This method uses a heap for storing the fragments
                    '''

        def resend_message(self, packet, mode=-1):
            if self.next_fragment == 0 and self.last == packet.get_packet():
                self.receive_Thread = None
                return
            if packet.is_it_right_crc():
                last_seg_num = 0
                varr = len(self.fragments)
                for i in range(varr):
                    curr = heapq.heappop(self.fragments)
                    while curr[1].get_frag_num() < packet.get_frag_num() and curr[
                        1].get_frag_num() >= self.next_fragment:
                        if curr[1].get_frag_num() == self.next_fragment:
                            self.assembled_message = self.assembled_message + curr[1].get_data()
                            last_seg_num = curr[1].get_seq_num()
                            self.next_fragment = self.next_fragment + 1


                        elif curr[1].get_frag_num() > self.next_fragment:

                            resend_pack = MyHeader.make_resend_request_message_packet(prev_seq_num=last_seg_num,
                                                                                      frag_num=self.next_fragment)
                            last = copy.deepcopy(self.next_fragment)
                            anm = 0
                            while True:
                                self.send_to_server(resend_pack)
                                # resend_pack.get_all_data()

                                while last == self.next_fragment:
                                    anm = anm + 1
                                    if anm == 10000:
                                        break

                                if anm != 10000:
                                    break
                                anm = 0

                            # self.next_fragment = self.next_fragment + 1
                            # print('NEXT FRAG = ', self.next_fragment)

                if mode == 1:
                    self.next_fragment = self.next_fragment + 1
                    self.assembled_message = self.assembled_message + packet.get_data()

                    self.ra_recieved = False
                    while not self.ra_recieved:
                        self.send_to_server(MyHeader.make_res_ack_message_packet(packet.get_seq_num()))
                        time.sleep(0.1)


                else:
                    self.send_to_server(MyHeader.make_ack_end_message_packet(packet.get_seq_num()))
                    print("[*] Message transfer successful")
                    self.assembled_message = self.assembled_message + packet.get_data()
                    print("Amount of fragments: ", self.next_fragment+1, "\nAmount of bytes:",len(self.assembled_message))
                    print(self.assembled_message.decode())

                    self.assembled_message = b""
                    self.next_fragment = 0
                    self.last = packet.get_packet()


                    self.receiving_in_progress = False

                self.receive_Thread = None

        '''
        Menu is for choosing different options such as sending message,file or changing the fragment size and info about the fragment size and current path
            '''

        def menu(self):
            while True:
                print(print(''''
                    [+] By default the CLIENT is the sender of data
                    [*]Menu:
                    1. Send message
                    2. Send file
                    3. change fragment size
                    4. info 
                    5. file directory
                    

                    '''))
                command = input(">> ")
                print(command)
                if command == "1":
                    message = input("message>> ")
                    print('[*] Message transfer in progress...')
                    self.send_message(message)

                    while self.transfer_in_progress != -1:
                        time.sleep(0.1)
                if command == "2":
                    filepath = input("absolute file path>> ")
                    try:
                        txt = filepath.rsplit('\\', 1)
                        print(txt)
                        filepath = txt[0]
                        filepath = filepath + "\\"
                        filename = txt[1]
                        print(filepath, filename)

                        dest = input("destination path, dont write anything if you want it in the predefined directory>>")
                        print('[*] File transfer in progress...')
                        self.send_file(filepath, filename, dest)
                    except Exception:
                        print(Exception)
                        print("Wrong input")
                        pass
                if command == "3":
                    message = input("max fragment size>> ")
                    try:
                        Constants.max_fragment_size = int(message)
                        self.fragment_size = int(message) * 8
                    except Exception:
                        print("Error input should be an integer")
                        pass
                if command == "4":
                    print('[*] Information \nMax fragment size :  ', Constants.max_fragment_size, "bytes",
                          '\nCurrent path: ', self.path)
                if command=="5":
                    path = input("file save directory>> ")
                    self.path=path



        '''
        This method is responsible for starting the connection with the server and keeping it alive through the keep_alive packets.
        The self.active_communication variable starts as false, when it is false, the client will start counting for 15 seconds and will send keep alive packets, if in that 15 seconds
        there are no packets being sent, then it will close the connection
            '''

        def connect(self):
            counter = 0
            while not self.connected:
                try:
                    packet = MyHeader.make_syn_package()
                    self.send_to_server(packet)

                    time.sleep(2)

                except Exception as e:
                    self.clientSocket.close()
                    self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    self.connected = False
                    time.sleep(2)
                    counter = 0
            while self.connected:
                if not self.active_communication:
                    packet = MyHeader.make_keep_alive_packet(self.prev_seq_num)

                    self.keep_alive = True
                    self.receiving_in_progress = False
                    self.send_to_server(packet)
                    counter = counter + 1
                    time.sleep(5)
                    if counter == 5 and not self.active_communication:
                        self.connected = False
                        print("The connection is not active anymore")

                else:
                    counter = 0
                    self.keep_alive = False
                    self.active_communication = False
                    time.sleep(5)

            connect(self)

        '''
        This method has its own thread which is constantly listening the server for the packets. Whenever it captures the packet it will
        react according to the type and flag of the packet.
            '''

        def receive(self):
            while True:
                try:
                    recpacket = MyHeader.MyHeader(self.receive_packet())
                    self.prev_seq_num = recpacket.get_seq_num()
                    if self.last_sent_packet is not None:

                        if self.keep_alive is True:

                            if recpacket.get_flag() == 'AK':

                                self.active_communication = True
                            if recpacket.get_flag() == 'K':

                                self.active_communication = True
                                packet_to_send = MyHeader.make_keep_alive_ack_packet(self.prev_seq_num)

                                self.send_to_client(packet_to_send)


                        else:
                            self.active_communication = True

                            if recpacket.get_flag() == 'SA':
                                self.connected = True

                            elif recpacket.get_flag() == 'K':
                                packet = MyHeader.make_keep_alive_ack_packet(self.prev_seq_num)

                                self.send_to_server(packet)

                            elif recpacket.get_flag() == 'AE' and recpacket.get_type() == 3:
                                print("Recieved ACK END packet :", recpacket.get_all_data())
                                self.end_received = 1
                                self.transfer_in_progress = -1
                                self.fragments_sent = []

                            elif recpacket.get_flag() == 'AE' and recpacket.get_type() == 1:
                                print("Recieved ACK END packet :", recpacket.get_all_data())
                                self.end_received = 1
                                self.transfer_in_progress = -1
                                self.fragments_sent = []

                            elif recpacket.get_flag() == 'AE' and recpacket.get_type() == 2:
                                print("Recieved ACK END packet :", recpacket.get_all_data())
                                self.transfer_in_progress = -1
                                self.end_received = 1
                                self.fragments_sent = []

                            elif recpacket.get_flag() == 'AE' and recpacket.get_type() == 4:
                                print("Recieved ACK END packet :", recpacket.get_all_data())
                                self.end_received = 1
                                self.transfer_in_progress = -1
                                self.fragments_sent = []


                            elif recpacket.get_flag() == 'R' and recpacket.get_type() == 3 and self.transfer_in_progress != -1:
                                print("Recieved RESEND packet :", recpacket.get_all_data())
                                if self.resend_in_prog == 1:
                                    self.resend_in_prog = 2
                                else:
                                    self.end_received = 1
                                num = recpacket.get_frag_num() % Constants.memory_limit

                                packet = self.fragments_sent[num]
                                print("Sending back missing fragment :", packet.get_all_data())

                                self.send_to_server(packet)







                            elif recpacket.get_flag() == 'AR' and recpacket.get_type() == 3:
                                print("Recieved ACK RESEND packet :", recpacket.get_all_data())
                                self.resend_in_prog = 0
                                self.fragments_sent = []

                            elif recpacket.get_flag() == 'R' and recpacket.get_type() == 4 and self.transfer_in_progress != -1:
                                print("Recieved RESEND packet :", recpacket.get_all_data())
                                if self.resend_in_prog == 1:
                                    self.resend_in_prog = 2
                                else:
                                    self.end_received = 1

                                num = recpacket.get_frag_num() % Constants.memory_limit

                                packet = self.fragments_sent[num]
                                print("Sending back missing fragment :", packet.get_all_data())
                                self.send_to_server(packet)

                                self.send_to_server(packet)





                            elif recpacket.get_flag() == 'AR' and recpacket.get_type() == 4:
                                print("Recieved ACK RESEND packet :", recpacket.get_all_data())
                                self.resend_in_prog = 0
                                self.fragments_sent = []

                            ## server side

                            elif recpacket.get_type() == 1 and recpacket.get_flag() == 'E':

                                if self.crntpacket is None or recpacket.get_crc() != self.crntpacket:
                                    print("[*] Message transfer successful")
                                    self.crntpacket = recpacket.get_crc()
                                    print(recpacket.get_data().decode())

                                    packet_to_send = MyHeader.make_ack_end_nonfarag_message_packet(recpacket.get_seq_num())
                                    self.send_to_server(packet_to_send)


                            elif recpacket.get_type() == 2 and recpacket.get_flag() == 'E':
                                if recpacket.is_it_right_crc():
                                    print("Recieved filename message :", recpacket.get_all_data())
                                    self.name_of_file = recpacket.get_data().decode()
                                    self.create_file(recpacket.get_data().decode())
                                    packet_to_send = MyHeader.make_ack_end_filename_packet(recpacket.get_seq_num())
                                    self.send_to_server(packet_to_send)
                                else:
                                    print("Recieved corrupted packet: ", recpacket.get_all_data())

                            elif recpacket.get_type() == 3 and recpacket.get_flag() is None:
                                self.ra_recieved = True
                                if recpacket.is_it_right_crc():
                                    print("Recieved message packet :",recpacket.get_all_data())



                                    if recpacket.get_frag_num() % Constants.memory_limit == 0 and recpacket.get_frag_num() != 0:
                                        if self.receive_Thread is None:
                                            self.receive_Thread = threading.Thread(target=resend_message,
                                                                                   args=(self, recpacket, 1,))
                                            self.receive_Thread.start()

                                    elif self.next_fragment == recpacket.get_frag_num():
                                        self.next_fragment = self.next_fragment + 1
                                        self.assembled_message = self.assembled_message + recpacket.get_data()
                                    elif recpacket.get_frag_num() > self.next_fragment:
                                        try:
                                            heapq.heappush(self.fragments, (recpacket.get_frag_num(), recpacket))
                                        except Exception:
                                            pass
                                else:
                                    print("Corrupted packet: ", recpacket.get_all_data())


                            elif recpacket.get_type() == 3 and recpacket.get_flag() == 'E':
                                print("Recieved message packet :", recpacket.get_all_data())
                                if self.receive_Thread is None:
                                    self.receive_Thread = threading.Thread(target=resend_message, args=(self, recpacket,))
                                    self.receive_Thread.start()

                            elif recpacket.get_type() == 4 and recpacket.get_flag() is None:
                                self.ra_recieved = True
                                if recpacket.is_it_right_crc():
                                    print("Recieved file packet :", recpacket.get_all_data())

                                    if recpacket.get_frag_num() % Constants.memory_limit == 0 and recpacket.get_frag_num() != 0:
                                        if self.receive_Thread is None:
                                            self.receive_Thread = threading.Thread(target=resend_file,
                                                                                   args=(self, recpacket, 1,))
                                            self.receive_Thread.start()

                                    elif self.next_fragment == recpacket.get_frag_num():
                                        self.next_fragment = self.next_fragment + 1


                                        self.file.write(recpacket.get_data())

                                    elif recpacket.get_frag_num() > self.next_fragment:
                                        try:
                                            heapq.heappush(self.fragments, (recpacket.get_frag_num(), recpacket))
                                        except Exception:
                                            pass
                                else:
                                    print("Corrupted packet: ", recpacket.get_all_data())


                            elif recpacket.get_type() == 4 and recpacket.get_flag() == 'E':
                                print("Recieved file packet :", recpacket.get_all_data())
                                if self.receive_Thread is None:
                                    self.receive_Thread = threading.Thread(target=resend_file, args=(self, recpacket,))
                                    self.receive_Thread.start()







                except Exception:

                    continue

        run(self)


print('Input the IP address of the server.')

address = input(">> ")
print('Input the port of the server.')
port = input(">> ")
try:
    port = int(port)
except Exception:
    print("Error input should be an integer")
    port = Constants.server_port
    pass

client = Client(Constants.client_ip, Constants.client_port, address, port)
