import time, logging, queue, threading
from sim import MSSimThread

class Worker(MSSimThread):

	def __init__(self,
				t_name,
				incoming_pipeline,
				outgoing_pipeline,
				process,
				min_random_wait_to_read=0.02,
				max_random_wait_to_read=0.03,
				incoming_pipeline_timeout=0.1,
				outgoing_pipeline_timeout=0.2,
				):
		if not self.parm_check(min_random_wait_to_read,max_random_wait_to_read):
			return None
		
		super().__init__()
		self.process = process
		self.incoming_pipeline = incoming_pipeline
		self.outgoing_pipeline = outgoing_pipeline
		self.t_name = t_name
		self.children["process"] = self.process
		self.conf["min_random_wait_to_read"] = min_random_wait_to_read
		self.conf["max_random_wait_to_read"] = max_random_wait_to_read
		self.conf["incoming_pipeline_timeout"] = incoming_pipeline_timeout
		self.conf["outgoing_pipeline_timeout"] = outgoing_pipeline_timeout
		self.conf["running"] = True

	def parm_check(self,min_wait,max_wait):
		ok = True
		if (min_wait>max_wait):
			logging.debug(
				"{}: Worker initialized with bad parameters, \
				min_random_wait_to_read must be smaller than \
				max_random_wait_to_read but {} > {}".format(
									self.t_name,
									self.conf["min_random_wait_to_read"],
									self.conf["outgoing_pipeline_timeout"]))
			ok = False
		return ok

	def run(self):
		logging.debug("{} thread started ...".format(self.t_name))
		while(self.conf["running"]):
			try:
				device_id,request_id = self.incoming_pipeline.get(timeout=self.conf["incoming_pipeline_timeout"])
			except queue.Empty :
				continue
			self.process.execute(device_id,request_id)
			self.outgoing_pipeline.put((device_id,request_id),timeout=self.conf["outgoing_pipeline_timeout"])
 

	def stop(self):
		logging.info("{} stopping worker ...".format(self.t_name))
		self.conf["running"] = False
