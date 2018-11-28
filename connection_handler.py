import queue, time, logging

class ConnectionHandler():
	# TODO IMPLEMENT TIMEOUT

	def __init__(self):
		self.connections = {}
		self.sorted_connections = []
		

	def __str__(self):
		return "ConnectionManager"

	def add_connection(self,socket,address,device_id,request_id):
		t_now = time.time()

		conn = {}
		conn['t_s'] = t_now
		conn['address'] = address
		conn['socket'] = socket
		conn['device_id'] = device_id

		self.connections[request_id] = conn

	def get_next_connection_socket(self,device_id,request_id):
		s = self.get_connection_socket(device_id,request_id)
		return s

	def get_connection_socket(self,device_id,request_id):
		 s = self.connections[request_id]['socket']
		 return s

	def delete_connection(self,device_id,request_id):
		del self.connections[request_id]

	def delete_all_connections():
		keys = list(self.connections.keys())
		for k in keys:
			self.delete_connection("",k)


	def get_connections(self):
		return self.connections

	def get_all_sockets(self):
		sockets = []
		for request_id in self.connections.keys():
			sockets.append(self.connections[request_id]["socket"])
		return sockets	

	def close_connections(self):
		for k in self.connections.keys():
			self.connections[k]['socket'].close()

	def clean(self, timeout):
		t_now = time.time()
		keys = list(self.connections.keys())
		for k in keys:
			if (t_now - self.connections[k]['t_s']) > timeout:
				self.delete_connection("",k)

