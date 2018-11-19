import datetime, socket, threading, queue, logging, os, time, random 

#class Network(threading.Thread,Reporter):

class Network(threading.Thread):
	''' meta networking class'''

	def __init__(self
				connection_name=None,
				listen_host="localhost",
				listen_port=5090,
				maximum_number_of_listen_clients=1000,
				manager=self
				):

		if connection_name = None:
			connection_name = str(random.getrandbits(16))
		else:
			self.connection_name = connection_name
		
		self.connections = {}

		self.to_worker_pipeline = queue.Queue()

		self.source = Source(connection_name=connection_name+"_Source"
							pipeline=self.to_worker_pipeline,
							maximum_number_of_clients=maximum_number_of_listen_clients,
							host=listen_host,
							port=listen_port
							)
		#self.sink = 

		self.running = True


	def  __str__(self):
		return "Network_{}".format(self.connection_name)

	def run(self):
		while(running):
			# clean broken connections

			time.sleep(2)


	def add_connection(self,socket,address,request_id,device_id):
		t_now = time.time()
		conn = {}
		conn['address'] = address
		conn['socket'] = socket
		self.connections[request_id] = conn

	def get_connection_socket(self,request_id,device_id):
		 socket = self.connections[request_id]['socket']
		 self.delete_connection(request_id,device_id)
		 return socket

	def delete_connection(self,request_id,device_id):
		del self.connections[request_id]

	

	def into_worker_pipeline(self,request_id,device_id):
		''' expect tuple ....'''
		pass

	def get_worker_pipeline(self):
		return self.to_worker_pipeline

	def set_worker_pipeline(self,pipeline):
		self.to_worker_pipeline = pipeline

	def set_sink_pipeline(self):
		pass

	def get_sink_pipeline(self):
		pass


	def get_stats(self):
		pass
		# inheritance reporter

	def reset_stats(self):
		pass
		# inheritance reporter

	def stop(self):
		self.running = False
		self.source.stop()
		self.sink.stop()
		logging.debug("Stopping {} ...".format(self.__str__))

class Source(threading.Thread):

	def __init__(self,connection_name,pipeline,manager,maximum_number_of_clients=1000,host="localhost",port=5090):
		self.connecton_name = connection_name + "_Source"
		if host == None:
			host = "localhost"
		self.pipeline = pipeline
		self.host = host
		self.port = port
		self.maximum_number_of_clients = maximum_number_of_clients

		self.manager= manager
		self.error = 0

		self.running= True
		super().__init__()

	def __str__(self):
		return "{}".format(self.connection_name) 		

	def run(self):
		serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		serversocket.bind((self.host,self.port))
		serversocket.listen(self.maximum_number_of_clients)
		logging.info("server is now listening on port {}".format(self.port))
		while self.running: 
			(socket, address, msg) = serversocket.accept()
			manager.add_connection(socket,address)

			# TODO change to DEVICE and REQUEST ID
			#request_id = 
			self.manager.into_worker_pipeline(request_id,device_id)


