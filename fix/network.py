#!/usr/bin/env python3
'''Network manager class for FIX'''

from socket import *
from fix.log import *
import threading,  _thread
from threading import Thread, Lock
import time
import functools
from queue import Queue
import logging
#import fix44
from fix.fix44  import  FIX44
#from  multiprocessing import Queue

def threading_deco(func):
    ''' Threading decorator. '''    
    @functools.wraps(func)
    def wrap(*args, **kw):
        thr_proc = threading.Thread(target = func, args = args, kwargs = kw).start()
    return wrap

def synchronized(lock):
    ''' Synchronization decorator. '''
    #@functools.wraps(lock)
    def wrap(func):
        def sync_function(*args, **kw):            
            try:
              lock.acquire()
              return func(*args, **kw)   
            finally:
              lock.release()
        return sync_function
    return wrap
    
client_locker = Lock()
process_locker = Lock()
server_locker = Lock()
  
HOST='127.0.0.1'
PORT=9121
BUF = 10240

########################################################################

class Client(Thread):

  def connect(self):
    print('connecting to:' ,self.addr)
    self.soc = socket(AF_INET, SOCK_STREAM) # create a TCP socket
    self.soc.connect(self.addr)
    self.begin_listening()
    
  def set_queues(self):
    self.process_queue = Queue()
    self.send_queue = Queue()
  

  def __init__(self, host = HOST,  port = PORT,  process_function = None, silent = False, fix = None, log_level = logging.CRITICAL ):
      Thread.__init__(self) 
      self.mutex = Lock()
      self.log_in = fix.SenderCompId +'.in'
      self.log_out = fix.SenderCompId +'.out'  
      self.LOGGER = FIX_Log(silent, self.log_in, self.log_out)
      self.addr = (host,  port)
      #self.soc = socket(AF_INET, SOCK_STREAM) # create a TCP socket
      #self.soc.connect(self.addr)
      self.data=''
      self.process_function = process_function
      self.BUF = BUF
      #self.begin_listening()
      self.silent = silent
      self.set_queues()
      self.fix = fix
      
      # Connect
      self.connect()
      
      #HeartBeat
      self.run_hertbeats = False
      self.hertbeats_running = False
      self.hertbeat_interval = 30
      
      self.log_level = log_level
      logging.basicConfig(filename='Client.log',level = self.log_level)
       

  def print(self, text):
    if (self.silent is False):
      print (text)

  def set_process_function(self, process_function):
    self.fix.customer_processor = process_function

  def begin_listening(self):
      try:
          self.listen()
      except Exception as e:
          logging.critical('Exception is '+str (e) ) 

  def get_self(self):
    return self

  def send(self,  msg):
    try:
      self.send_queue.put(msg)
    except Exception as exc:
     logging.critical('Queue Exception: ', exc)
      
  def send_msg(self,  msg):
    try:
      self.soc.send(msg.encode())
      self.print(' Client OUT: '+msg)
      self.LOGGER.log_out_msg(msg)
    except Exception as exc:
     logging.critical('Socket Exception: ', exc)
   
  def send_x_times(self,  msg, x = 1):
    for k in range(x):
      try:
        self.soc.send(msg.encode())
        print (' Client OUT: '+msg)
        self.LOGGER.log_out_msg(msg)
      except Exception as exc:
       logging.critical('Socket Exception: ', exc)
  
  @threading_deco
  def listen(self):
      threading.Thread(target = self.processor).start()
      threading.Thread(target = self.sender).start()
      threading.Thread(target = self.start_heart_beats).start()
      while True:
          self.data = self.soc.recv(self.BUF )          
          if self.data:
              data = self.data.decode('CP1251')
              self.print(' Client IN: '+str(data))
              if  data is not '':
                logging.debug(' put '+str(data)+' IN process_queue')
                splitted_msg = self.LOGGER.log_in_msg(data)
                for msg in splitted_msg:
                  if msg is not None:
                    self.process_queue.put(msg)
                logging.debug(' PUT process_queue size = '+ str(self.process_queue.qsize()))

  def sender(self):  
    while True:
        try:
          logging.debug(' start_loop send_queue size = '+ str(self.send_queue.qsize()))          
          to_send = self.send_queue.get()
          if to_send is not None:
              self.send_msg(to_send)         
          logging.debug(' end_loop send_queue size = '+ str(self.send_queue.qsize()))   
        except Exception as exc:
            logging.critical('sender Exception: ', exc)
             
  def processor(self):  
    while True:
        try:
          logging.debug(' start_loop process_queue size = '+ str(self.process_queue.qsize()))
          to_process = self.process_queue.get() #block=False
          logging.debug(' end_loop process_queue size = '+ str(self.process_queue.qsize()))
          reply = self.process(to_process)
        except Exception as exc:
            logging.critical('processor Exception: ', exc)
    
  def process(self, msg):
      self.fix.customer_processor(msg, self) 
    
  def run(self):
      self.listen()
  
  def start_heart_beats(self):
      if(self.hertbeats_running is False):          
          self.hertbeats_running = True            
          while(self.fix.session_is_active):
            if (self.run_hertbeats is True):
              logging.debug('self.run_hertbeats is True')  
              msg = self.fix.generate_Heartbeat_35_0()
              self.send(msg)
              time.sleep(self.hertbeat_interval)
          self.hertbeats_running = False
##########################################################################

class SessionsManager(object):
  def __init__ (self, server_name = 'Server'):
    self.server_name = server_name
    self.ssn_dict = {}
    pass
  
  def get_session(self, msg):
    ''' take FIX message and return session for it. If session is not exists - creates it
        store sessions just by senders. Targets will the same.  '''
    sender = FIX44().get_tag(msg, 49)
    
    pass

#@Thread
class Server( Client ):  

  '''def set_queues(self):
    super(Server, self).set_queues()'''
    
  #def __init__(self, host = '',  port = PORT,  process_function = None, silent = False, log_in = 'server_fix_log.in', log_out = 'server_fix_log.out', sleep = 0.5 ):
  def __init__(self, host = HOST,  port = PORT,  process_function = None, silent = False, Name = 'Server', sleep = 0.5, log_level = logging.CRITICAL ):
      Thread.__init__(self) 
      self.mutex = Lock()
      self.log_in = Name +'.in'
      self.log_out = Name +'.out'  
      self.LOGGER = FIX_Log(silent, self.log_in, self.log_out)
      self.addr = (host,  port)
      #self.soc = socket(AF_INET, SOCK_STREAM) # create a TCP socket
      #self.soc.connect(self.addr)
      self.data=''
      self.process_function = process_function
      self.BUF = BUF
      #self.begin_listening()
      self.silent = silent
      self.sleep = sleep
      self.set_queues()
      self.connect()
      self.connections_list = []
      self.connections = {}
      self.sessions = {} #Dictionary
      #self.ssn_mngr = SessionsManager(Name)
      self.log_level = log_level
      logging.basicConfig(filename=Name+'.log',level = self.log_level, format='%(asctime)s %(levelname)s %(message)s',)
      
        
  '''def begin_listening(self):
      self.listen()'''
      
  def sessions_handler(self, msg):
    logging.debug(' sessions_handler msg: '+msg)
    t_fix = FIX44()
    sender = t_fix.get_tag(msg, 49)
    target = t_fix.get_tag(msg, 56)
    key_exists = sender in self.sessions
    if ( not key_exists ) or (self.sessions[sender] is None):
      fix=FIX44()
      fix.init(target, sender, self.process_function) # incoming sender is out coming target
      self.sessions[sender] = fix
      logging.debug(' Create FIX session for '+sender)      
    else:
      logging.debug(' FIX session for '+sender+' allready exists')
      
    logging.debug(' sessions_handler return '+str(self.sessions[sender].get_randomID()))
    return self.sessions[sender]

  def print(self, text):
    if (self.silent is False):
      print (text)
  '''def set_process_function(self, process_function):
    #self.process_function = process_function
    self.fix.customer_processor = process_function'''
      
  def run(self):
      self.listen()

  def listen_data(self):
    while True:
      for connect in self.connections_list: 
        try:
          if connect == None:
            self.print(' Server self.connect == None ')
            break
          data = connect.recv(self.BUF )
          logging.debug('Receive new data')
          if not data:
            self.print(' Server NO  self.data ')            
            #break
          else:
            data = data.decode('CP1251')
            logging.debug(' Server IN: '+str(data))
            self.print(' Server IN: '+str(data))
            print(' Server IN: '+str(data))
            if  data is not '':
              logging.debug(' put '+str(data)+' IN process_queue')
              splitted_msg = self.LOGGER.log_in_msg(data)
              for msg in splitted_msg:
                if msg is not None:
                  t_fix = FIX44()
                  sender = t_fix.get_tag(msg, 49)
                  self.connections[sender] = connect
                  self.process_queue.put(msg)
            #self.process(self.data.decode('CP1251'))
            #self.fix.customer_processor(self.data.decode('CP1251'), self)
        except Exception as exc:
          print('Socket Exception: ', exc)
          self.soc.close()

  def listen_connection(self, connect):
    while True:
      try:
          data = connect.recv(self.BUF )
          logging.debug('Receive new data')
          if not data:
            self.print(' Server NO  self.data ')            
            #break
          else:
            data = data.decode('CP1251')
            logging.debug(' Server IN: '+str(data))
            self.print(' Server IN: '+str(data))
            print(' Server IN: '+str(data))
            if  data is not '':
              logging.debug(' put '+str(data)+' IN process_queue')
              splitted_msg = self.LOGGER.log_in_msg(data)
              for msg in splitted_msg:
                if msg is not None:
                  t_fix = FIX44()
                  sender = t_fix.get_tag(msg, 49)
                  self.connections[sender] = connect
                  self.process_queue.put(msg)
            #self.process(self.data.decode('CP1251'))
            #self.fix.customer_processor(self.data.decode('CP1251'), self)
      except Exception as exc:
          print('Socket Exception: ', exc)
          self.soc.close()
          
          
  @threading_deco
  def listen(self):
      threading.Thread(target = self.processor).start()
      threading.Thread(target = self.sender).start()
      #threading.Thread(target = self.listen_data).start()
      #threading.Thread(target = self.start_heart_beats).start()
      print('listen for connection')
      while True:      
          connect, addr = self.soc.accept()
          self.connections_list.append(connect)
          threading.Thread(target = self.listen_connection, args=(connect,)).start()
          self.print('new connection detected: '+str(self.addr))
          logging.debug('new connection detected: '+str(self.addr))
          self.print(' Server listening')      
      self.print(' Server STOPPED listening')      
      
  def process(self, msg):
    logging.debug(' Server process '+str(msg))
    self.print(' Server process '+str(msg))
    #self.fix.customer_processor(msg, self) 
    if msg is not '':
      logging.debug(' self.process_function '+str(msg))
      self.process_function(msg, self)

  '''def send(self,  msg):
    try:
      self.send_queue.put(msg)
    except Exception as exc:
     logging.critical('Queue Exception: ', exc)'''
      
  def send_msg(self,  msg):
    try:
      t_fix = FIX44()
      target = t_fix.get_tag(msg, 56)    
      logging.debug(' send_msg = '+str(msg))
      logging.debug(' send_msg target = '+target)
      conn = self.connections[target]
      conn.send(msg.encode())
      #self.connect.send(msg.encode())
      self.print(' Server OUT: '+msg)
      self.LOGGER.log_out_msg(msg)
    except Exception as exc:
     logging.critical(' send_msg Socket Exception: ', exc)
                     
  def connect(self):
    self.soc = socket(AF_INET, SOCK_STREAM)
    #self.soc.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    self.soc.bind(self.addr)      
    self.soc.listen(5)  
    self.begin_listening()
    


