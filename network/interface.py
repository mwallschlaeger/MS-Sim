import queue
import logging
import datetime
import multiprocessing

from network.fork_handler import ForkHandler
from sim import MSSimObject
from network.packet import MSSimPacket,MSSimHeader
import helper

class NetworkInterface(MSSimObject):

	def __init__(self,
				t_name=None,
				multiprocessing_worker=False,
				queue_maxsize=1000, 
				put_work_task_timeout=0.05,
				pull_work_task_timeout=0.05):

		super().__init__()

		# configure ForkHandler
		self.fork_handler = ForkHandler()
		self.connections = {}

		if t_name is None:
			t_name = str(random.getrandbits(16))
		else:
			self.t_name = t_name

		self.children["ForkHandler"] = self.fork_handler
		self.conf["put_work_task_timeout"] = put_work_task_timeout
		#self.conf["pull_work_task_timeout"] = pull_work_task_timeout
		self.conf["multiprocessing_worker"] = multiprocessing_worker
		self.conf["queue_maxsize"] = queue_maxsize
		self.conf["recv_bytes"] = 409622
		self.metrics["encoding_error"] = 0
		self.metrics["full_queue_error"] = 0
		self.metrics["put_to_pipeline"] = 0
		self.metrics["pulled_from_pipeline"] = 0
		self.metrics["const_start_time"] = None
		self.metrics["const_stop_time"] = None
		self.send_pipeline = helper.get_queue(	multiprocessing_worker=self.conf["multiprocessing_worker"],
												maxsize=self.conf["queue_maxsize"])

	def __str__(self):
		return "Network_{}".format(self.t_name)

	def add_forward_pl(self,pl):
		self.fork_handler.add_fork(pl,100)

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

	def put_work_task(self,packet):
		pipeline = self.children["ForkHandler"].get_random_pipeline()
		if pipeline is None:
			return False
		else:
			try:
				pipeline.put((packet),timeout=self.conf["put_work_task_timeout"])
				self.metrics["put_to_pipeline"] += 1
			except queue.Full as QF1:
				logging.debug(
					"{}; full pipeline in fork {} in {} ...".format(
											self.t_name,
											fork_count,
											str(self.fork_handler.fork_list)))
				self.metrics["full_queue_error"] += 1
				logging.debug("{}".format(str(QF1)))
				return False
		return True

	def pull_work_result(self):
		self.metrics["pulled_from_pipeline"] += 1
		packet = self.send_pipeline.get()
		return packet

	def pull_task_done(self):
		if not self.conf["multiprocessing_worker"]:
			self.send_pipeline.task_done()
			
	def get_send_pipeline(self):
		return self.send_pipeline