import queue, time, logging, copy
from sim import MSSimObject

class ConnectionHandler(MSSimObject):
	# TODO IMPLEMENT TIMEOUT

	def __init__(self):
		super().__init__()

		self.connections = {}
		self.t_name = "ConnectionHandler"
		self.metrics["deleted_connections"] = 0
		self.metrics["cleaned_connections"] = 0
		self.metrics["key_errors"] = 0 # race condition
	def __str__(self):
		return self.t_name

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
		try:
			del self.connections[request_id]
			self.metrics["deleted_connections"] += 1
		except KeyError:
			self.metrics["key_errors"] += 1


	def delete_all_connections(self):
		keys = list(self.connections.keys())
		for k in keys:
			self.delete_connection("",k)


	def get_connections(self):
		return self.connections

	def get_all_sockets(self):
		sockets = []
		keys = list(self.connections.keys())
		for request_id in keys:
			sockets.append(self.connections[request_id]["socket"])
		return sockets	

	def close_all_connections(self):
		for k in self.connections.keys():
			self.connections[k]["socket"].close()

	def clean(self, timeout):
		t_now = time.time()
		keys = list(self.connections.keys())
		for k in keys:
			try:
				if (t_now - self.connections[k]["t_s"]) > timeout:
					self.metrics["cleaned_connections"] += 1
					self.connections[k]["socket"].close()
					self.delete_connection("",k)
			except KeyError:
				self.metrics["key_errors"] += 1
