import queue,logging, random

from connection_handler import ConnectionHandler
from fork_handler import ForkHandler

class NetworkInterface(ForkHandler,ConnectionHandler):

	def __init__(self,t_name=None,queque_maxsize=1000, put_work_task_timeout=0.01):

		if t_name == None:
			t_name = str(random.getrandbits(16))
		else:
			self.t_name = t_name
		
		self.put_work_task_timeout = put_work_task_timeout
		self.before_work_pipeline = queue.Queue(maxsize=queque_maxsize)
		self.after_work_pipeline = queue.Queue(maxsize=queque_maxsize)

		# configure ForkHandler
		ForkHandler.__init__(self)
		# set default entry
		self.add_fork(probability=100,pipeline=self.before_work_pipeline)
		ConnectionHandler.__init__(self)

	def __str__(self):
		return "Network_{}".format(self.t_name)

	def build_msg(self,device_id,request_id):
		msg = None 
		try:
			msg = device_id + request_id
		except:
			logging.warning("wrong encoding. device_id: {}, request_id: {}, msg: {} ...".format(device_id,request_id,msg))
			return None
		return msg

	def read_msg(self,data):
		try:
			device_id = data[0:12]
			request_id = data[12:27]
			return device_id,request_id
		except:
			return None,None
		return None,None 

	def start(self):
		self.source.start()
		self.sink.start()

	def stop(self):
		logging.info("Stopping {} ...".format(str(self)))
		self.source.stop()
		self.sink.stop()

	def join(self):
		self.sink.join()
		self.source.join()

	def put_work_task(self,device_id,request_id):
		fork_count = 0
		for probability,pipeline in self.fork_list:
			r = random.randint(1,100)
			if probability >= r:
				try:
					pipeline.put((device_id,request_id),timeout=self.put_work_task_timeout) # TODO configurable value
				except queue.Full as QF1:
					logging,debug(
						"Full Pipeline of Fork {} in {} of Network {}!".format(
												fork_count,
												str(self.fork_list),
												self.__str__())
												)
					logging.warning("{}".format(str(QF1)))
					# QOS_METRIC TO REPORT!
					# TODO: respond overload to client!
				finally:
					return 0
			fork_count+=1
		logging.debug("Request {} from device {} lost, due to missconfiguration in fork_list".format(request_id,device_id))
		return -1
		# QOS_METRIC TO REPORT!
	
	def pull_work_result(self,timeout=0.01):
		device_id,request_id = self.after_work_pipeline.get(timeout=timeout)
		return device_id,request_id

	def pull_task_done(self):
		self.after_work_pipeline.task_done()

	def get_before_work_pipeline(self):
		return self.before_work_pipeline

	def get_after_work_pipeline(self):
		return self.after_work_pipeline