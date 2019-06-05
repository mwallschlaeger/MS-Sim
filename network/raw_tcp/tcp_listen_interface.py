import datetime
import socket
import queue
import logging
import os
import time
import random
import threading
import select

import network.raw_tcp.tcp_marshaller as tcp_marshaller
from network.interface import NetworkInterface
from sim import MSSimObject,MSSimThread

class ListenNetworkInterface(NetworkInterface):
	
	''' meta networking class '''
	def __init__(self,
				t_name=None,
				listen_host="localhost",
				listen_port=5090,
				listen_timeout=0.5,
				maximum_number_of_listen_clients=10000,
				multiprocessing_worker=False,
				queue_maxsize=1000,
				put_work_task_timeout=0.05,
				pull_work_task_timeout=0.05
				):

		MSSimObject.__init__(self)
		NetworkInterface.__init__(self,
								t_name=t_name+"_Listen",
								multiprocessing_worker=multiprocessing_worker,
								queue_maxsize=queue_maxsize,
								put_work_task_timeout=put_work_task_timeout,
								pull_work_task_timeout=pull_work_task_timeout
								)

		self.source = Source(t_name=t_name+"_Listen",
							network=self,
							listen_timeout=listen_timeout,
							maximum_number_of_clients=maximum_number_of_listen_clients,
							host=listen_host,
							port=listen_port,
							)
		
		self.sink = Sink(t_name=t_name+"_Listen",
						network=self)
		self.request_to_socket = {}
		self.children["source"] = self.source
		self.children["sink"] = self.sink

class Source(MSSimThread):

	def __init__(self, 
				t_name, 
				network, 
				listen_timeout, 
				maximum_number_of_clients=1000, 
				host="localhost", 
				port=5090):

		super().__init__()
		self.network = network
		self.serversocket = None
		self.t_name = t_name + "Source"
		if host == None:
			self.conf["host"] = "localhost"
		self.conf["host"] = host
		self.conf["port"] = port
		self.conf["maximum_number_of_clients"] = maximum_number_of_clients
		self.conf["listen_timeout"] = listen_timeout
		self.conf["running"] = True
		self.metrics["socket_error"] = 0
		self.metrics["socket_timeout_error"] = 0
		self.metrics["to_many_open_files_error"] = 0
		self.metrics["closed_sockets_by_error"] = 0

	def __str__(self):
		return self.t_name 		

	def initialize_socket(self,timeout=2):
		serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		serversocket.bind((self.conf["host"],self.conf["port"]))
		serversocket.listen(self.conf["maximum_number_of_clients"])
		logging.info("{}: server is now listening on port {}".format(self.t_name,self.conf["port"]))		
		return serversocket

	def run(self):
		inputs = []
		data_dict = {}
		while self.conf["running"]:
			if not self.serversocket:
				self. serversocket = self.initialize_socket() 
				inputs = [self.serversocket]
			read_sockets, __, error_sockets = select.select(
									inputs,
									[],
									inputs,
									1)

			for sock in read_sockets:
				if sock is self.serversocket:
					(sock, address) = self.serversocket.accept()
					logging.info("{}: Establishing connection to {}".format(self.t_name,address))
					sock.setblocking(0)
					inputs.append(sock)
					data_dict[sock] = b''
				else:
					try:
						data = sock.recv(self.network.conf["recv_bytes"])
						if data == b'':
							error_sockets.append(sock)
						logging.debug("{}: receiving data: {}".format(self.t_name,data))
						data_dict[sock] += data
					except:
						error_sockets.append(sock)
						continue 

					while True:
						data_dict[sock], packet = tcp_marshaller.unmarshall(data_dict[sock])
						if not packet:
							break
						self.network.put_work_task(packet)
						self.network.request_to_socket[packet.header.request_id] = sock

			for sock in error_sockets:
				if sock:
					logging.error("{}: Closing broken socket {} ...".format(self.t_name,sock))
					sock.close()
				inputs.remove(sock)
				del data_dict[sock]


	def stop(self):
		logging.info("{}: stopping ...".format(self.t_name))
		self.conf["running"] = False

''' sending packets to other hosts '''
class Sink(MSSimThread):
	def __init__(self, t_name, network):
		super().__init__()
		self.network = network
		self.t_name = t_name + "Sink"
		self.conf["running"] = True
		self.metrics["reading_on_empty_queue"] = 0
		self.metrics["connection_list_error"] = 0
		self.metrics["closed_sockets_by_error"] = 0

	def __str__(self):
		return self.t_name

	def run(self):
		logging.info("{}: initialized ...".format(self.t_name))
		while(self.conf["running"]):
			packet = self.network.pull_work_result()
			sock = self.network.request_to_socket[packet.header.request_id]
			data = tcp_marshaller.marshall(packet)
			try:
				sock.send(data)
				logging.debug("{}: sending packet: {}".format(self.t_name,packet))
			except Exception as FT:
				logging.debug("{}: sending Message failed, connection already closed ...".format(self.t_name))
				self.metrics["closed_sockets_by_error"] += 1
				sock.close()
			finally:
				del self.network.request_to_socket[packet.header.request_id]			
			
			self.network.pull_task_done()

	def stop(self):
		self.conf["running"] = False
		logging.debug("{}: stopping ...".format(self.t_name))