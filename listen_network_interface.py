import datetime, socket, threading, queue, logging, os, time, random 
from network_interface import NetworkInterface

class ListenNetworkInterface(NetworkInterface):
	
	''' meta networking class '''
	def __init__(self,
				t_name=None,
				listen_host="localhost",
				listen_port=5090,
				maximum_number_of_listen_clients=10000,
				queque_maxsize=1000
				):

		NetworkInterface.__init__(self,t_name=t_name,queque_maxsize=queque_maxsize)

		self.source = Source(t_name=t_name,
							network=self,
							maximum_number_of_clients=maximum_number_of_listen_clients,
							host=listen_host,
							port=listen_port
							)
		
		self.sink = Sink(t_name=t_name,
						network=self
						)		

class Source(threading.Thread):

	DEVICE_ID_LEN = 12
	REQUEST_ID_LEN = 16

	#	Default Packet header
	# | 12 bytes Device_id | 16 bytes Request_id | Random Padding |

	def __init__(self,
				t_name,
				network,
				maximum_number_of_clients=1000,
				host="localhost",
				port=5090
				):

		self.t_name = t_name + "_Source"
		if host == None:
			host = "localhost"
		self.host = host
		self.port = port
		self.maximum_number_of_clients = maximum_number_of_clients

		self.network = network
		self.error = 0

		self.running= True
		super().__init__()

	def __str__(self):
		return self.t_name 		

	def initialize_socket(self,timeout=2):
		logging.info("initialized {} ...".format(self.__str__()))
		self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.serversocket.bind((self.host,self.port))
		self.serversocket.listen(self.maximum_number_of_clients)
		self.serversocket.settimeout(timeout)
		logging.info("server is now listening on port {}".format(self.port))
		
	def run(self):
		self.initialize_socket()
		while self.running: 
			acc_socket = None
			try:
				(acc_socket, address) = self.serversocket.accept()
			except socket.timeout as T1:
				if acc_socket is not None:
					acc_socket.close()
				continue
			except OSError as OS1:
				# TODO: may reduce maximum number of clients
				logging.error("TO many open files ...")
				logging.error("{}".format(str(OS1)))
				self.serversocket.close()
				self.initialize_socket()
				self.network.delete_all_connections()
				continue

			try:
				data = acc_socket.recv(4096)
			except InterruptedError as IE1:
				logging.warning("{}: Timeout while reading socket ...".format(str(self)))
				logging.warning("{}".format(str(IE1)))
				acc_socket.close()
				continue				
			except socket.timeout:
				acc_socket.close()
				continue

			device_id,request_id = self.network.read_msg(data)
			if device_id == None:
				acc_socket.close()
				continue
			logging.debug("recv packet on {}".format(str(self)))

			# TODO ODERING
			self.network.add_connection(acc_socket,address,device_id,request_id)
			self.network.put_work_task(device_id,request_id)

	def stop(self):
		logging.info("Stopping {} ...".format(str(self)))
		self.running = False
		#self.serversocket.close()

class Sink(threading.Thread):
	''' sending packets to other hosts '''
	def __init__(self,
				t_name,
				network
				):

		self.t_name = t_name + "_Sink"
		self.network = network # maybe not neccessary

		self.error = 0
		self.running = True

		#TOOD set timeout
		super().__init__()

	def __str__(self):
		return self.t_name

	def run(self):
		logging.info("initialized {} ...".format(self.__str__()))
		while(self.running):
			try:
				device_id, request_id = self.network.pull_work_result()
			except queue.Empty as E1:
				continue

			response_socket = self.network.get_next_connection_socket(device_id,request_id)

			if response_socket == None:
				logging.error("Could not found socket in connection history ...")
				# TODO try to delete ?
				continue

			self.network.delete_connection(device_id,request_id)
			msg = self.network.build_msg(device_id,request_id)

			try:
				response_socket.send(msg)
				logging.debug("send message with req_id: {} on {} ...".format(request_id,str(self)))
			except:
				logging.warning("sending Message to {} failed, closing connection ...".format(address))
				response_socket.close()
				self.error += 1
			self.network.pull_task_done()
			response_socket.close()
	
	def stop(self):
		self.running = False
		logging.info("Stopping {} ...".format(str(self)))