import datetime, socket, queue, logging, os, time, random, threading
from network_interface import NetworkInterface
from sim import MSSimObject,MSSimThread


class ListenNetworkInterface(NetworkInterface):
	
	''' meta networking class '''
	def __init__(self,
				t_name=None,
				listen_host="localhost",
				listen_port=5090,
				listen_timeout=0.5,
				maximum_number_of_listen_clients=10000,
				queque_maxsize=1000,
				put_work_task_timeout=0.05,
				pull_work_task_timeout=0.05
				):

		MSSimObject.__init__(self)
		NetworkInterface.__init__(self,
								t_name=t_name,
								queque_maxsize=queque_maxsize,
								put_work_task_timeout=put_work_task_timeout,
								pull_work_task_timeout=pull_work_task_timeout
								)

		self.source = Source(t_name=t_name,
							network=self,
							listen_timeout=listen_timeout,
							maximum_number_of_clients=maximum_number_of_listen_clients,
							host=listen_host,
							port=listen_port,
							)
		
		self.sink = Sink(t_name=t_name,
						network=self,
						)		
		self.children["source"] = self.source
		self.children["sink"] = self.sink

class Source(MSSimThread):

	def __init__(self, t_name, network, listen_timeout, maximum_number_of_clients=1000, host="localhost", port=5090):
		#super().__init__()

		super().__init__()
		self.network = network

		self.t_name = t_name + "_Source"
		if host == None:
			self.conf["host"] = "localhost"
		self.conf["host"] = host
		self.conf["port"] = port
		self.conf["maximum_number_of_clients"] = maximum_number_of_clients
		self.conf["listen_timeout"] = listen_timeout
		self.conf["running"] = True
		self.conf["DEVICE_ID_LEN"] = 12
		self.conf["REQUEST_ID_LEN"] = 16
		self.conf["RECV_BYTES"] = 4096
		self.metrics["socket_error"] = 0
		self.metrics["socket_timeout_error"] = 0
		self.metrics["to_many_open_files_error"] = 0
		self.metrics["closed_sockets_by_error"] = 0

	def __str__(self):
		return self.t_name 		

	def initialize_socket(self,timeout=2):
		logging.debug("{}: initialized ...".format(self.t_name))
		self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.serversocket.bind((self.conf["host"],self.conf["port"]))
		self.serversocket.listen(self.conf["maximum_number_of_clients"])
		self.serversocket.settimeout(self.conf["listen_timeout"])
		logging.info("{}: server is now listening on port {}".format(self.t_name,self.conf["port"]))
		
	def run(self):
		self.initialize_socket()
		while self.conf["running"]:
			acc_socket = None
			try:
				(acc_socket, address) = self.serversocket.accept()
			except socket.timeout as T1:
				self.metrics["socket_error"] += 1
				if acc_socket is not None:
					close_socket_by_error(acc_socket)
				continue
			except OSError as OS1:
				self.metrics["to_many_open_files_error"] += 1
				self.serversocket.close()
				self.initialize_socket()
				self.network.connection_handler.delete_all_connections()
				continue

			try:
				data = acc_socket.recv(self.conf["RECV_BYTES"])
			except InterruptedError as IE1:
				self.metrics["socket_timeout_error"] += 1
				logging.debug("{}: Timeout while reading socket ...".format(str(self)))
				logging.debug("{}".format(str(IE1)))
				self.metrics["closed_sockets_by_error"] += 1
				continue
			except socket.timeout:
				self.metrics["socket_timeout_error"] += 1
				self.metrics["closed_sockets_by_error"] += 1
				continue

			device_id,request_id = self.network.read_msg(data)
			if device_id == None:
				self.metrics["closed_sockets_by_error"] += 1
				acc_socket.close()
				continue

			self.network.connection_handler.add_connection(acc_socket,address,device_id,request_id)
			self.network.put_work_task(device_id,request_id)

	def stop(self):
		logging.info("{}: stopping ...".format(self.t_name))
		self.conf["running"] = False

''' sending packets to other hosts '''
class Sink(MSSimThread):
	def __init__(self, t_name, network):

		super().__init__()

		self.network = network

		self.t_name = t_name + "_Sink"
		self.conf["running"] = True
		self.metrics["reading_on_empty_queue"] = 0
		self.metrics["connection_list_error"] = 0
		self.metrics["closed_sockets_by_error"] = 0

	def __str__(self):
		return self.t_name

	def run(self):
		logging.info("{}: initialized ...".format(self.t_name))
		while(self.conf["running"]):
			try:
				device_id, request_id = self.network.pull_work_result()
			except queue.Empty as E1:
				self.metrics["reading_on_empty_queue"] += 1
				continue
			try:
				response_socket = self.network.connection_handler.get_next_connection_socket(device_id,request_id)
			except KeyError as KE1:
				self.metrics["connection_list_error"] = +1
				logging.debug("{}: Could not find socket in connection history ...".format(self.t_name))
				continue

			self.network.connection_handler.delete_connection(device_id,request_id)
			msg = self.network.build_msg(device_id,request_id)

			try:
				response_socket.send(msg)
			except:
				logging.debug("{}: sending Message to {} failed, closing connection ...".format(self.t_name,address))
				self.metrics["closed_sockets_by_error"] += 1
				response_socket.close()
			
			self.network.pull_task_done()
			response_socket.close()

	def stop(self):
		self.conf["running"] = False
		logging.debug("{}: stopping ...".format(self.t_name))