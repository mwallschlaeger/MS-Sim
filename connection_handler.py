import queue, time, logging

class ConnectionHandler():
	# TODO IMPLEMENT TIMEOUT

	def __init__(self, connection_timeout=2):
		self.connections = {}
		self.sorted_connections = []
		
		self.timeout = connection_timeout

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

	def get_connections(self):
		return self.connections

	def close_connections(self):
		for k in self.connections.keys():
			self.connections[k]['socket'].close()