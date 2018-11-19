import datetime, socket, threading, queue, logging, os, time 

class Sink(threading.Thread):

	def __init__(self,connection_name,pipeline,allowed_hosts,dst_host="localhost",dst_port=5090):
		self.connecton_name = connection_name + "_Sink"
		if dst_host == None:
			dst_host = "localhost"
		self.pipeline = pipeline
		self.dst_host = dst_host
		self.dst_port = dst_port
		self.error = 0

		self.running= True
		super().__init__()

	def __str__(self):
		return "{}".format(self.connection_name) 

	def run(self):
		logging.info("initialized {} ...".format(self.__str__()))
		while(self.running):
			if not self.pipeline.empty():
				(socket, address, msg) = pipeline.get_nowait()
				try:
					socket.send(msg)
				except:
					logging.debug("sending Message to {} failed, closing connection ...".format(address))
					socket.close()
					self.error += 1
			else:
				time.sleep(0.01)
				

