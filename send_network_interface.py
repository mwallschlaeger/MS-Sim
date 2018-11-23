import socket, threading, logging, random, select
from network_interface import NetworkInterface

class SendNetworkInterface(NetworkInterface):
	''' meta networking class'''

	def __init__(self,
				t_name=None,
				load_balancer=None,
				queque_maxsize=1000
				):

		NetworkInterface.__init__(self,t_name=t_name,queque_maxsize=queque_maxsize)

		# Check if no loadbalancer
		if load_balancer == None:
			logging.error("No Load Balancer defined ...")
			# TODO 
			global RUNNING
			RUNNING = False
			sys.exit(1)
				
		self.sink = Sink(t_name=t_name,
						network=self,
						load_balancer=load_balancer
						)
	

		self.source = Source(t_name=t_name,
							network=self,
							)

		
	def add_host(self,host,port):
		return self.load_balancer.add_host(host,port)

	def delete_host(self,host,port):
		return self.load_balancer.delete_host(host,port)

	def get_host_list(self):
		return self.load_balancer.host_list()

	def set_host_list(lst=[]):
		if (self.load_balancer.check_host_list(lst)):
			self.load_balancer.host_list = lst
		else: 
			return False

class Source(threading.Thread):

	DEVICE_ID_LEN = 12
	REQUEST_ID_LEN = 16

	#	Default Packet header
	# | 12 bytes Device_id | 16 bytes Request_id | Random Padding |

	def __init__(self,
				t_name,
				network,
				):

		self.t_name = t_name + "_Source"
		self.network = network

		self.error = 0
		self.running= True

		super().__init__()

	def __str__(self):
		return self.t_name 		

	def run(self):

		while self.running: 
			# TODO check if this thread goes crazy
			read_sockets, __, error_sockets = select.select(self.network.get_all_sockets() , [], [],0.4)
			ok = False
			for sock in read_sockets:
				ok = True
				
				# receive and process data
				try:
					data = sock.recv(4096)
				except InterruptedError as IE1:
					logging.warning("could not recv data properly. Closing socket ...")
					logging.warning("{}".format(str(IE1)))
					ok = False
				
				if len(data)==0:
					continue

				device_id,request_id = self.network.read_msg(data)
				if device_id == None:
					logging.warning("could not parse received msg properly in {} ...".format(str(self)))
					continue
				logging.debug("recv msg with req_id: {} on {}".format(request_id,str(self)))
				
				# post mgnt
				sock.close()
				self.network.delete_connection(device_id=device_id,request_id=request_id)
				if ok:
					self.network.put_work_task(device_id,request_id)


	def stop(self):
		self.running = False
		#TODO check how to improve
		logging.debug("Stopping {} ...".format(self.__str__))


''' sending packets to other hosts '''
class Sink(threading.Thread):
	def __init__(self,
				t_name,
				network,
				load_balancer,
				host_list=[]
				):

		self.t_name = t_name + "_LBSink"
		self.network = network 
		self.load_balancer = load_balancer

		self.error = 0
		self.running = True
		super().__init__()

	def __str__(self):
		return self.t_name

	def run(self):
		logging.info("initialized {} ...".format(self.__str__()))
		while(self.running):
			# get host from list
			device_id, request_id = self.network.pull_work_result()

			msg = self.network.build_msg(device_id,request_id)
			if msg== None:
				continue
			#try:
			send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			address = self.load_balancer.get_next_endpoint()
			if address == None:
				logging.warning("No loadbalancer endpoint defined, unable to send messages!")
				continue
			try:
				send_socket.connect(address)
			except InterruptedError as IE1: 	
				logging.warning("Connection timed out ...")
				continue
			try:	
				send_socket.send(msg)
				logging.debug("send message with req_id: {} on {} ...".format(request_id,str(self)))
			except: 
				send_socket.close()
				logging.warning("sending message failed on {} ...".format(str(self)))
				continue

			self.network.add_connection(socket=send_socket,address=address,device_id=device_id,request_id=request_id)

	def stop(self):
		self.running = False
		logging.debug("Stopping {} ...".format(self.__str__))