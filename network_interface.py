import queue,logging, random, datetime

from connection_handler import ConnectionHandler
from fork_handler import ForkHandler
from sim import MSSimObject

class NetworkInterface(MSSimObject):

	def __init__(self,t_name=None,queque_maxsize=1000, put_work_task_timeout=0.05,pull_work_task_timeout=0.05):

		super().__init__()

		# configure ForkHandler
		self.fork_handler = ForkHandler()

		self.connection_handler = ConnectionHandler()

		if t_name is None:
			t_name = str(random.getrandbits(16))
		else:
			self.t_name = t_name

		self.children["ForkHandler"] = self.fork_handler
		self.children["connection_handler"] = self.connection_handler
		self.conf["put_work_task_timeout"] = put_work_task_timeout
		self.conf["pull_work_task_timeout"] = pull_work_task_timeout
		self.conf["queque_maxsize"] = queque_maxsize
		self.metrics["encoding_error"] = 0
		self.metrics["full_queue_error"] = 0
		self.metrics["end_of_fork_list_error"] = 0
		self.metrics["put_to_pipeline"] = 0
		self.metrics["pulled_from_pipeline"] = 0
		self.metrics["const_start_time"] = None
		self.metrics["const_stop_time"] = None
		
		self.before_work_pipeline = queue.Queue(maxsize=self.conf["queque_maxsize"])
		self.after_work_pipeline = queue.Queue(maxsize=self.conf["queque_maxsize"])
		# set default entry
		self.fork_handler.add_fork(probability=100,pipeline=self.before_work_pipeline)

	def __str__(self):
		return "Network_{}".format(self.t_name)

	def build_msg(self,device_id,request_id):
		msg = None 
		try:
			msg = device_id + request_id
		except:
			self.metrics["encoding_error"] += 1
			logging.warning("{}: wrong encoding. device_id: {}, request_id: {}, msg: {} ...".format(self.t_name,device_id,request_id,msg))
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
		self.metrics["const_start_time"] = str(datetime.datetime.now())
		logging.debug("{}: starting ...".format(self.t_name))

		self.source.start()
		self.sink.start()

	def stop(self):
		self.metrics["const_stop_time"] = str(datetime.datetime.now())
		logging.debug("{}: stopping ...".format(self.t_name))
		self.source.stop()
		self.sink.stop()

	def join(self):

		self.sink.join()
		self.source.join()

	def put_work_task(self,device_id,request_id):
		fork_count = 0
		for probability,pipeline in self.fork_handler.conf["fork_list"]:
			r = random.randint(1,100)
			if probability >= r:
				try:
					pipeline.put((device_id,request_id),timeout=self.conf["put_work_task_timeout"])
					self.metrics["put_from_pipeline"] += 1
				except queue.Full as QF1:
					logging,debug(
						"{}; full pipeline in fork {} in {} ...".format(
												self.t_name,
												fork_count,
												str(self.fork_handler.fork_list)))
					self.metrics["full_queue_error"] += 1
					logging.debug("{}".format(str(QF1)))

					# QOS_METRIC TO REPORT!
					# TODO: respond overload to client!
				finally:
					return 0
			fork_count+=1
		logging.debug("{}: request {} from device {} lost, due to missconfiguration in fork_list".format(self.t_name,request_id,device_id))
		self.metrics["end_of_fork_list_error"] += 1
		return -1

	def pull_work_result(self):
		self.metrics["pulled_from_pipeline"] += 1
		device_id,request_id = self.after_work_pipeline.get(timeout=self.conf["pull_work_task_timeout"])
		return device_id,request_id

	def pull_task_done(self):
		self.after_work_pipeline.task_done()

	def get_before_work_pipeline(self):
		return self.before_work_pipeline

	def get_after_work_pipeline(self):
		return self.after_work_pipeline