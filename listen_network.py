import datetime, socket, threading, queue, logging, os, time, random 
from connection_handler import ConnectionHandler
from fork_handler import ForkHandler

class ListenNetwork(ForkHandler,ConnectionHandler):
	''' meta networking class'''

	def __init__(self,
				t_name=None,
				listen_host="localhost",
				listen_port=5090,
				maximum_number_of_listen_clients=1000,
				queque_maxsize=10000
				):

		if t_name == None:
			t_name = str(random.getrandbits(16))
		else:
			self.t_name = t_name
		
		self.before_work_pipeline = queue.Queue(maxsize=queque_maxsize)
		self.after_work_pipeline = queue.Queue(maxsize=queque_maxsize)
		

		# configure ForkHandler
		ForkHandler.__init__(self)
		self.add_fork(probability=100,pipeline=self.before_work_pipeline)

	

		self.source = Source(t_name=t_name,
							network=self,
							maximum_number_of_clients=maximum_number_of_listen_clients,
							host=listen_host,
							port=listen_port
							)
		

		self.sink = Sink(t_name=t_name,
						network=self
						)		
		ConnectionHandler.__init__(self)

	def __str__(self):
		return "Network_{}".format(self.t_name)

	def start(self):
		self.source.start()
		self.sink.start()

	def stop(self):
		self.source.stop()
		self.sink.stop()
		logging.debug("Stopping {} ...".format(self.__str__))

	def put_work_task(self,device_id,request_id):
		fork_count = 0
		for probability,pipeline in self.fork_list:
			r = random.randint(1,100)
			if probability >= r:
				try:
					pipeline.put((device_id,request_id),timeout=0.01) # TODO configurable value
				except queue.Full as QF1:
					logging,debug("Full Pipeline of Fork {} in {} of Network {}!".format(fork_count,str(self.fork_list),self.__str__()))
					logging.warning("{}".format(str(QF1)))
					# QOS_METRIC TO REPORT!
					# TODO: respond overload to client!
				finally:
					return 0
			fork_count+=1
		logging.debug("Request {} from device {} lost, due to missconfiguration in fork_list".format(request_id,device_id))
		return -1
		# QOS_METRIC TO REPORT!

	def pull_work_result(self,timeout=None):
		try:			
			device_id,request_id = self.after_work_pipeline.get(timeout=timeout)
		except queue.Empty as CM1:
			return None,None
		return device_id,request_id

	def get_before_work_pipeline(self):
		return self.before_work_pipeline

	def get_after_work_pipeline(self):
		return self.after_work_pipeline


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

	def initialize_socket(self):
		logging.info("initialized {} ...".format(self.__str__()))
		self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.serversocket.bind((self.host,self.port))
		self.serversocket.listen(self.maximum_number_of_clients)
		logging.info("server is now listening on port {}".format(self.port))
		
	def run(self):
		self.initialize_socket()
		while self.running: 
			try:
				(acc_socket, address) = self.serversocket.accept()
			except OSError as OS1:
				# TODO: may reduce maximum number of clients
				logging.error("TO many open files ...")
			
			# TODO NEEDS DOUBLECHECK
			data = acc_socket.recv(4096)
			device_id = data[0:12]
			request_id = data[13:28]

			# TODO ODERING
			self.network.add_connection(acc_socket,address,device_id,request_id)
			self.network.put_work_task(device_id,request_id)

	def stop(self):
		self.running = False
		self.serversocket.close()
		self.manager.close()
		logging.debug("Stopping {} ...".format(self.__str__))


class Sink(threading.Thread):
	''' sending packets to other hosts '''
	def __init__(self,
				t_name,
				network,
				#lb_func=None
				):

		self.t_name = t_name + "_Sink"
		self.network = network # maybe not neccessary

		self.error = 0
		self.running = True
		super().__init__()

	def __str__(self):
		return self.t_name

	def run(self):
		logging.info("initialized {} ...".format(self.__str__()))
		while(self.running):
			device_id, request_id = self.network.pull_work_result()
			response_socket = self.network.get_next_connection_socket(device_id,request_id)
			self.network.delete_connection(device_id,request_id)

			if response_socket == None:
				logging.error("Could not found socket in connection history ...")
				# TODO try to delete ?
				continue
			try:
				response_socket.send(bytes("response!","utf-8"))
			except:
				logging.debug("sending Message to {} failed, closing connection ...".format(address))
				acc_socket.close()
				self.error += 1
			response_socket.close()
	
	def stop(self):
		self.running = False
		logging.debug("Stopping {} ...".format(self.__str__))