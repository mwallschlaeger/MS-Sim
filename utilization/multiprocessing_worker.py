import time, logging, queue, threading
from sim import MSSimThread, MSSimMultiProcessing
import helper

class MultiprocessingWorker(MSSimMultiProcessing):

	def __init__(self,
				t_name,
				incoming_pipeline,
				outgoing_pipeline,
				default_process,
				min_random_wait_to_read=0.02,
				max_random_wait_to_read=0.03,
				incoming_pipeline_timeout=0.1,
				outgoing_pipeline_timeout=0.2,
				):
		if not helper.worker_parm_check(t_name,min_random_wait_to_read,max_random_wait_to_read):
			return None
			
		super().__init__()
		self.incoming_pipeline = incoming_pipeline
		self.outgoing_pipeline = outgoing_pipeline
		self.t_name = t_name
		self.conf["processes_with_type"] = [] # tuple list (process,type)
		self.conf["default_process"] = default_process
		self.conf["min_random_wait_to_read"] = min_random_wait_to_read
		self.conf["max_random_wait_to_read"] = max_random_wait_to_read
		self.conf["incoming_pipeline_timeout"] = incoming_pipeline_timeout
		self.conf["outgoing_pipeline_timeout"] = outgoing_pipeline_timeout
		self.conf["running"] = True

	def add_process(self,process,request_type):
		self.conf["processes_with_type"].append((process,request_type))

	def run(self):
		logging.debug("{} thread started ...".format(self.t_name))
		while(self.conf["running"]):
			try:
				packet = self.incoming_pipeline.get(timeout=self.conf["incoming_pipeline_timeout"])
			except queue.Empty :
				continue
			for pt in self.conf["processes_with_type"]:
				process,request_type = pt
				if packet.header.request_type == request_type:
					process.execute(packet)
					self.outgoing_pipeline.put(packet,timeout=self.conf["outgoing_pipeline_timeout"])
					continue
			self.conf["default_process"].execute(packet)
			self.outgoing_pipeline.put(packet,timeout=self.conf["outgoing_pipeline_timeout"])
 
	def stop(self):
		logging.info("{}: stopping worker ...".format(self.t_name))
		self.conf["running"] = False
