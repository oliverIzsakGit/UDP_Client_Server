import zlib
from random import randint

import bitarray
from bitarray.util import ba2int
import Constants

'''This class is responsible for creating,checking and organizing the packets that are being sent between the server and client
'''


class MyHeader:
    '''
    The initialize method has 2 responsibilities . 1 is to create a packet and 2. is to organize the fields of a packet received in bytes.
    1.When creating a packet the protocol header will take up either 9 or 13 bytes. Depending on whether there is a fragment number contained in the packet or not.
    Since flag packets (packets that do not contain data, but they contain flags such as:syn,ack,res,end,ka) do not need a fragment number, their header only takes up
    9 bytes.Furthermore, the header contains a type(0-4,flag packet,message,file,fragmented-message,fragmented_file), sequence number which is randomly generated at first and gets
    incremented with the length of the data being sent,crc for checking whether the packet got corrupted, and optional is the fragment number.

    '''

    def __init__(self, data, prev_seq=-1, type=-1, syn=-1, ack=-1, res=-1, ka=-1, end=-1, fragment_number=-1):
        if type == -1:  ## If no type field is given then the function of the initialize is to separate the fields of a packet received in bytes
            self.right_crc = False
            bits = bitarray.bitarray()
            bits.frombytes(data)
            self.type = bits[:3]  ## type takes up 3 bits
            self.flag = bits[3:8]  ## flag 5 bits

            self.sequence_number = bits[8:40]  ## sequence number 4 bytes.
            if prev_seq == -1:  ## if sequence number is -1 ,means this is the first packet being sent.
                self.data_lenght = 0
            else:
                if prev_seq < ba2int(self.sequence_number):
                    self.data_lenght = Constants.max_sqn - prev_seq + ba2int(self.sequence_number)
                else:
                    self.data_lenght = ba2int(self.sequence_number) - prev_seq
            self.crc = bits[40:72]  ## 32 bits are reserved for the crc.
            if ba2int(
                    self.type) > 2:  ##if type is bigger than 2, which means its either a fragmented file or message, then we will have 32 bits reserved for fragment number.
                self.fragment_number = bits[72:104]
                self.data = bits[104:]
                crc1 = (zlib.crc32(
                    self.type + self.flag + self.sequence_number + self.fragment_number + self.data))  ## crc calculation
            else:  ## if the type is smaller than 2 , then we dont need fragment numbers.
                self.data = bits[72:]
                crc1 = (zlib.crc32(self.type + self.flag + self.sequence_number + self.data))
            self.all = data

            if self.check_crc(crc1):
                self.right_crc = True

        else:  ## if type is given either 0,1,2,3 or 4, then we are creating the packet
            self.right_crc = True
            my_bits = bitarray.bitarray()
            my_bits.frombytes(type.to_bytes(1, byteorder='big'))
            self.type = my_bits[5:8]  ## making the type field.
            flag = bitarray.bitarray()
            flag.append(syn)  ## creating the flag field
            flag.append(ack)
            flag.append(res)
            flag.append(ka)
            flag.append(end)
            self.flag = flag

            a = 0

            if fragment_number > -1:
                my_bits = bitarray.bitarray()
                my_bits.frombytes(fragment_number.to_bytes(4, byteorder='big'))
                self.fragment_number = my_bits
                a = 1
            else:
                self.fragment_number = None
            my_bits = bitarray.bitarray()
            bit_len = bitarray.bitarray()
            my_bits.frombytes(data)
            size = len(my_bits)
            bit_len.frombytes(size.to_bytes(2, byteorder='big'))
            self.data_lenght = bit_len
            self.data = my_bits
            x=size+prev_seq

            if (size + prev_seq) > Constants.max_sqn:  ##avoiding sequence number overflow

                ##while (x < Constants.max_sqn):
                  ##  x = x + 1
                    ##prev_seq = prev_seq - 1
                m = Constants.max_sqn
                x=(size+prev_seq)-m
                print(x)

            my_bits = bitarray.bitarray()
            my_bits.frombytes((x).to_bytes(4, byteorder='big'))
            self.sequence_number = my_bits

            my_bits = bitarray.bitarray()
            if a == 1:
                crc1 = (zlib.crc32(
                    self.type + self.flag + self.sequence_number + self.fragment_number + self.data)).to_bytes(4,
                                                                                                               byteorder='big')
            else:
                crc1 = (zlib.crc32(self.type + self.flag + self.sequence_number + self.data)).to_bytes(4,
                                                                                                       byteorder='big')
            my_bits.frombytes(crc1)
            self.crc = my_bits
            all = self.type + self.flag + self.sequence_number + self.crc
            if a == 1:
                all = all + self.fragment_number

            self.datas = data
            self.all = all.tobytes() + data

    def get_type(self):
        return ba2int(self.type)

    def set_Corrupted(self):
        if self.crc[0] == 1:
            self.crc[0] = 0
        else:
            self.crc[0] = 1
        if self.fragment_number is None:
            all = self.type + self.flag + self.sequence_number + self.crc
        else:
            all = self.type + self.flag + self.sequence_number + self.fragment_number + self.crc

        self.all = all.tobytes() + self.datas

    def get_flag(self):
        str1 = ''

        if self.flag[0] == 1:
            str1 = str1 + 'S'
        if self.flag[1] == 1:
            str1 = str1 + 'A'
        if self.flag[2] == 1:
            str1 = str1 + 'R'
        if self.flag[3] == 1:
            str1 = str1 + 'K'
        if self.flag[4] == 1:
            str1 = str1 + 'E'
        if str1 == '':
            str1 = None
        return str1

    def set_flag(self, str1):

        if str1._contains_('S'):
            self.flag[0] = 1
        else:
            self.flag[0] = 0

        if str1._contains_('A'):
            self.flag[1] = 1
        else:
            self.flag[1] = 0

        if str1._contains_('R'):
            self.flag[2] = 1
        else:
            self.flag[2] = 0

        if str1._contains_('K'):
            self.flag[3] = 1
        else:
            self.flag[3] = 0

        if str1._contains_('E'):
            self.flag[4] = 1
        else:
            self.flag[4] = 0

    def get_data_length(self):
        return self.data_lenght

    def get_crc(self):
        return ba2int(self.crc)

    def check_crc(self, crc):
        if ba2int(self.crc) == crc:
            return True
        else:
            return False

    def get_packet(self):
        return self.all

    def get_seq_num(self):
        return ba2int(self.sequence_number)

    def get_frag_num(self):
        return ba2int(self.fragment_number)

    def get_all_data(self):


        try:
            if self.fragment_number is not None:
                print("type: ", self.get_type(), "flag: ", self.get_flag(), "sequence no.: ", self.get_seq_num(),
                      "fragment no.: ", self.get_frag_num(), "data: ", self.data.tobytes(), sep='|')
            else:
                print("type: ", self.get_type(), "flag: ", self.get_flag(), "sequence no.: ", self.get_seq_num(),
                      "data: ", self.data.tobytes(), sep='|')
        except:
            print("type: ", self.get_type(), "flag: ", self.get_flag(), "sequence no.: ", self.get_seq_num(),
                  "data: ", self.data.tobytes(), sep='|')

        return self.right_crc

    def is_it_right_crc(self):
        return self.right_crc

    def get_data(self):
        return self.data.tobytes()


def make_syn_package():
    seq_num = randint(0, Constants.max_sqn)
    packet = MyHeader(''.encode('utf-8'), seq_num, 0, 1, 0, 0, 0, 0)
    return packet


def make_syn_ack_package(prev_seq_num):
    packet = MyHeader(''.encode('utf-8'), prev_seq_num, 0, 1, 1, 0, 0, 0)
    return packet


def make_keep_alive_packet(prev_seq_num):
    packet = MyHeader(''.encode('utf-8'), prev_seq_num, 0, 0, 0, 0, 1, 0)
    return packet


def make_keep_alive_ack_packet(prev_seq_num):
    packet = MyHeader(''.encode('utf-8'), prev_seq_num, 0, 0, 1, 0, 1, 0)
    return packet


def make_nonfragmented_message_packet(data, prev_seq_num):
    packet = MyHeader(data, prev_seq_num, 1, 0, 0, 0, 0, 1)
    return packet


def make_nonfragmented_file_packet(data, prev_seq_num):
    packet = MyHeader(data, prev_seq_num, 2, 0, 0, 0, 0, 1)
    return packet


def make_fragmented_message_packet(data, prev_seq_num, frag_num):
    packet = MyHeader(data, prev_seq_num, 3, 0, 0, 0, 0, 0, frag_num)
    return packet


def make_fragmented_file_packet(data, prev_seq_num, frag_num):
    packet = MyHeader(data, prev_seq_num, 4, 0, 0, 0, 0, 0, frag_num)
    return packet


def make_resend_request_message_packet(prev_seq_num, frag_num):
    packet = MyHeader(''.encode(), prev_seq_num, 3, 0, 0, 1, 0, 0, fragment_number=frag_num)
    return packet


def make_resend_request_file_packet(prev_seq_num, frag_num):
    packet = MyHeader(''.encode(), prev_seq_num, 4, 0, 0, 1, 0, 0, frag_num)
    return packet


def make_end_message_packet(data, prev_seq_num, frag_num):
    packet = MyHeader(data, prev_seq_num, 3, 0, 0, 0, 0, 1, frag_num)
    return packet


def make_end_file_packet(data, prev_seq_num, frag_num):
    packet = MyHeader(data, prev_seq_num, 4, 0, 0, 0, 0, 1, frag_num)
    return packet


def make_ack_end_message_packet(prev_seq_num):
    packet = MyHeader(''.encode(), prev_seq_num, 3, 0, 1, 0, 0, 1)
    return packet


def make_ack_end_nonfarag_message_packet(prev_seq_num):
    packet = MyHeader(''.encode(), prev_seq_num, 1, 0, 1, 0, 0, 1)
    return packet




def make_ack_end_file_packet(prev_seq_num):
    packet = MyHeader(''.encode(), prev_seq_num, 4, 0, 1, 0, 0, 1)
    return packet


def make_ack_end_filename_packet(prev_seq_num):
    packet = MyHeader(''.encode(), prev_seq_num, 2, 0, 1, 0, 0, 1)
    return packet


def make_res_ack_message_packet(prev_seq_num):
    packet = MyHeader(''.encode(), prev_seq_num, 3, 0, 1, 1, 0, 0)
    return packet


def make_res_ack_file_packet(prev_seq_num):
    packet = MyHeader(''.encode(), prev_seq_num, 4, 0, 1, 1, 0, 0)
    return packet


make_syn_package()

