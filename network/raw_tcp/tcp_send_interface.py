import socket
import threading
import logging
import random
import select
import sys
import queue
import time

from network.interface import NetworkInterface
import network.raw_tcp.tcp_marshaller as tcp_marshaller
from sim import MSSimObject,MSSimThread


class SendNetworkInterface(NetworkInterface):
	''' meta networking class'''

	def __init__(self,
				load_balancer,
				t_name="SendNetworkInterface",
				select_timeout=1,
				multiprocessing_worker=False,
				queue_maxsize=1000,
				put_work_task_timeout=0.05,
				pull_work_task_timeout=0.05
				):
		self.connections = {}
		NetworkInterface.__init__(self,
								t_name=t_name,
								queue_maxsize=queue_maxsize,
								multiprocessing_worker=multiprocessing_worker,
								put_work_task_timeout=put_work_task_timeout,
								pull_work_task_timeout=pull_work_task_timeout
								)
		self.c_lock = threading.Lock()


		self.sink = Sink(t_name=t_name + "_Send",
						network=self,
						load_balancer=load_balancer,
						)
		self.children[t_name+"_Sink"] = self.sink
		self.source = Source(t_name=t_name + "_Send",
							network=self,
							select_timeout=select_timeout
							)
		self.children[t_name+"_Source"] = self.source


	def get_address_for_connection(self,sock):
		for k,v in self.connections.items():
			if v == sock:
				return k
		return None

	def get_connection_for_address(self,address):
		if address in self.connections:
			s = self.connections[address]
		else:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect(address)
			s.setblocking(0)
			self.c_lock.acquire()
			self.connections[address] = s
			self.c_lock.release()
			logging.info("{}: Established connection to {} ...".format(self.t_name, str(address)))
		return s

	def close_socket(self,address):
		if address in self.connections:
			logging.error("{}: Closing broken socket {}...".format(self.t_name,self.get_connection_for_address(address)))
			self.connections[address].close()
			self.c_lock.acquire()
			del self.connections[address]
			self.c_lock.release()

	def get_socket_list(self):
		l = []
		self.c_lock.acquire()
		for k,v in self.connections.items():
			l.append(v)
		self.c_lock.release()
		return l

class Source(MSSimThread):

	def __init__(self, t_name, network, select_timeout=1):
		super().__init__()
		self.network = network
		self.t_name = t_name + "Source"
		self.conf["select_timeout"] = select_timeout 
		self.conf["running"] = True
		self.metrics["closed_sockets"] = 0
		self.metrics["packet_timeouts"] = 0
		self.metrics["list_latency"] = []
		self.metrics["recv_packets"] = 0
	def __str__(self):
		return self.t_name

	def run(self):
		data_dict = {}
		while self.conf["running"]:
			inputs = self.network.get_socket_list()
			if len(inputs) == 0:
				time.sleep(0.5)
				continue

			try:
				read_sockets, __, error_sockets = select.select(
									inputs,
									 [],
									 inputs,
									 1)
			except ValueError:
				logging.debug("socket closed, but not properly removed fom connections dict, implement locks if happening to often.")
				self.metrics["closed_sockets"]+=1 
				continue
			except OSError:
				logging.debug("Socket closed, but not properly removed.")
				self.metrics["closed_sockets"]+=1
				continue
			for sock in read_sockets:
				if sock not in data_dict:
					data_dict[sock] = b''
				try:
					data = sock.recv(self.network.conf["recv_bytes"])
					self.metrics["recv_packets"] += 1
				except ConnectionResetError:
					error_sockets.append(sock)
					continue
				except OSError:
					error_sockets.append(sock)
					continue
				if data == b'':
					error_sockets.append(sock)
					continue
				logging.debug("{}: receiving data: {}".format(self.t_name,data))
				data_dict[sock] += data

				while True:
					data_dict[sock], packet = tcp_marshaller.unmarshall(data_dict[sock])
					if not packet:
						break
					latency = self.network.get_latency(packet)
					if not latency:
						self.metrics["packet_timeouts"] += 1
					else:
						self.metrics["list_latency"].append(latency) 
					self.network.put_work_task(packet)
				
			for sock in error_sockets:
				self.metrics["closed_sockets"] += 1
				del data_dict[sock]
				self.network.c_lock.acquire()
				addr = self.network.get_address_for_connection(sock)
				self.network.c_lock.release()
				self.network.close_socket(addr)
	
	def stop(self):
		self.conf["running"] = False
		logging.debug("{}: stopping  ...".format(str(self)))

''' sending packets to other hosts '''
class Sink(MSSimThread):
	def __init__(self, t_name, network, load_balancer):
		super().__init__()
		self.network = network 
		self.load_balancer = load_balancer
		self.t_name = t_name + "Sink"
		self.children["load_balancer"] = load_balancer
		self.conf["running"] = True
		self.metrics["connection_timeouts"] = 0
		self.metrics["establishing_error"] = 0
		self.metrics["no_lb_endpoint_error"] = 0
		self.metrics["closed_sockets"] = 0
		self.metrics["send_packets"] = 0

	def __str__(self):
		return self.t_name

	def run(self):
		logging.debug("{}: initialized ...".format(str(self)))
		while self.conf["running"]:
			send_socket = None

			packet = self.network.pull_work_result()
			msg = tcp_marshaller.marshall(packet)			
			address = self.load_balancer.get_next_endpoint()
			if address is None:
				self.metrics["no_lb_endpoint_error"] += 1
				logging.warning("{}: No loadbalancer endpoint defined, unable to send messages ...".format(self.t_name))
				continue
			try:
				send_socket = self.network.get_connection_for_address(address)
			except ConnectionRefusedError as CRE1:
				self.metrics["connection_timeouts"] += 1
				logging.debug("{}: connection timeout ...".format(self.t_name))
				self.network.close_socket(address)
				self.network.pull_task_done()
				continue
			except socket.gaierror:
				self.metrics["establishing_error"] += 1
				logging.debug("{}: hostname error ...".format(self.t_name))
				self.network.close_socket(address)
				self.network.pull_task_done()
				continue
			except OSError:
				self.metrics["establishing_error"] += 1
				logging.debug("{}: No route to host {} ...".format(self.t_name,address))

			try:
				send_socket.send(msg)
				self.metrics["send_packets"] += 1
				logging.debug("{}: sending packet: {}".format(self.t_name,packet))
			except: 
				self.network.close_socket(address)
				self.metrics["closed_sockets"] += 1
				logging.warning("{}: sending packet failed  ...".format(self.t_name))
				continue
			finally:
				self.network.save_timestamp(packet)
				self.network.pull_task_done()

	def stop(self):
		self.conf["running"] = False
		logging.debug("{}: stopping  ...".format(str(self)))
