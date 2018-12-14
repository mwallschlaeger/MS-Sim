import time, logging, queue, threading

class Worker(threading.Thread):

	def __init__(self,
				incoming_pipeline,
				outgoing_pipeline,
				process,
				min_random_wait_to_read=0.02,
				max_random_wait_to_read=0.03):
	
		if (min_random_wait_to_read>max_random_wait_to_read):
			logging.warning(
				"Worker initialized with bad parameters, \
				min_random_wait_to_read must be smaller than \
				max_random_wait_to_read but {} > {}".format(
													min_random_wait_to_read,
													max_random_wait_to_read))
			return None

		self.min_random_wait_to_read=min_random_wait_to_read
		self.max_random_wait_to_read=max_random_wait_to_read
		self.process = process
		self.incoming_pipeline = incoming_pipeline
		self.outgoing_pipeline = outgoing_pipeline

		self.running = True
		super().__init__()

	def __str__(self):
		# TODO may not work properly
		return(super.__str__(self))

	def run(self):
		logging.debug("{} thread started ...".format(self.__str__()))
		while(self.running):
			try:
				device_id,request_id = self.incoming_pipeline.get(timeout=0.1)
			except queue.Empty :
				continue
			self.process.execute(device_id,request_id)
			self.outgoing_pipeline.put((device_id,request_id),timeout=0.2)
 

	def stop(self):
		logging.info("Stopping Worker {} ...".format(self.__str__()))
		self.running = False
