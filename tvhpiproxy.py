#!/usr/bin/python
# Tvheadend proxy to get XBMC on Raspberry Pi to work with Tvheadend
# Licensed under the GPL
import socket
import select
import time
import sys

# But when buffer get to high or delay go too down, you can broke things
delay = 0.0001

def int2bin ( i ):
  return chr(i >> 24 & 0xFF) + chr(i >> 16 & 0xFF)\
    + chr(i >> 16 & 0xFF) + chr(i & 0xFF)

def bin2int ( d ):
  return (ord(d[0]) << 24) + (ord(d[1]) << 16)\
    + (ord(d[2]) <<  8) + ord(d[3])

# HTSMSG types
HMF_MAP  = 1
HMF_S64  = 2
HMF_STR  = 3
HMF_BIN  = 4
HMF_LIST = 5

# Deserialize an htsmsg
def htsmsg_binary_deserialize ( data ):
  msg = {}
  while len(data) > 5:
    typ  = ord(data[0])
    nlen = ord(data[1])
    dlen = bin2int(data[2:6])
    data = data[6:]

    if len < nlen + dlen: raise Exception('not enough data')
    
    name = data[:nlen]
    data = data[nlen:]
    if typ in [ HMF_STR, HMF_BIN ]:
      item = data[:dlen]
    elif typ == HMF_S64:
      item = 0
      i    = dlen - 1
      while i >= 0:
        item = (item << 8) | ord(data[i])
        i    = i - 1
    elif typ in [ HMF_LIST, HMF_MAP ]:
      item = htsmsg_binary_deserialize(data[:dlen])
    else:
      raise Exception('invalid data type %d' % typ)
    msg[name] = item
    data      = data[dlen:]
  return msg


class Forward:
  def __init__(self):
    self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  def start(self, host, port):
    try:
      self.forward.connect((host, port))
      return self.forward
    except Exception, e:
      print e
      return False

class TheServer:
  input_list = []
  channel = {}

  def __init__(self, host, port, targethost, targetport):
    self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.server.bind((host, port))
    self.server.listen(200)
    self.icount = 0
    self.targethost = targethost
    self.targetport = targetport

  def main_loop(self):
    self.input_list.append(self.server)
    while 1:
      time.sleep(delay)
      ss = select.select
      inputready, outputready, exceptready = ss(self.input_list, [], [])
      for self.s in inputready:
        if self.s == self.server:
          self.on_accept()
          break

        self.length = self.s.recv(4)
        if len(self.length) < 4:
          self.on_close()
          break

        num  = bin2int(self.length)
        if num > 1024*1024*128:
          self.on_close()
          break

        self.data = ''
        while len(self.data) != num:
          tmp  = self.s.recv(num - len(self.data))
          if not tmp: self.on_close()
          self.data = self.data + tmp
          self.msg = htsmsg_binary_deserialize(self.data)

        if len(self.data) == num:
          self.on_recv()

  def on_accept(self):
    forward = Forward().start(self.targethost, self.targetport)
    clientsock, clientaddr = self.server.accept()
    if forward:
      print clientaddr, "has connected"
      self.input_list.append(clientsock)
      self.input_list.append(forward)
      self.channel[clientsock] = forward
      self.channel[forward] = clientsock
    else:
      print "Can't establish connection with remote server.",
      print "Closing connection with client side", clientaddr
      clientsock.close()

  def on_close(self):
    print self.s.getpeername(), "has disconnected"
    #remove objects from input_list
    self.input_list.remove(self.s)
    self.input_list.remove(self.channel[self.s])
    out = self.channel[self.s]
    # close the connection with client
    self.channel[out].close()  # equivalent to do self.s.close()
    # close the connection with remote server
    self.channel[self.s].close()
    # delete both objects from channel dict
    del self.channel[out]
    del self.channel[self.s]

  def on_recv(self):
    if self.msg.get('method','') == 'subscriptionStart':
      self.icount = 0
      self.channel[self.s].send(self.length)
      self.channel[self.s].send(self.data.replace('height@\x04\x02\x08', 'height8\x04\x02\x08')) 
    else:
      if self.msg.get('method','') == 'muxpkt':
        if self.msg.get('frametype', -1) == 73:
          self.icount = self.icount + 1
        if self.icount > 1:
          self.channel[self.s].send(self.length)
          self.channel[self.s].send(self.data)	
      else:
        self.channel[self.s].send(self.length)
        self.channel[self.s].send(self.data)

if __name__ == '__main__':
  if len( sys.argv ) == 4:
    server = TheServer('', int( sys.argv[1] ), sys.argv[2], int( sys.argv[3] ))
  else:
    server = TheServer('', 9983, '127.0.0.1', 9982)
  while 1:
    try:
      server.main_loop()
    except KeyboardInterrupt:
      print "Ctrl C - Stopping server"
      sys.exit(1)
    except Exception, e:
      print "Error:", e
