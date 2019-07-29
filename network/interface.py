import queue
import logging
import datetime
import multiprocessing
import time

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
		self.conf["multiprocessing_worker"] = multiprocessing_worker
		self.conf["queue_maxsize"] = queue_maxsize
		self.conf["max_latency_to_accept"] = 3
		self.conf["recv_bytes"] = 409622
		self.metrics["encoding_error"] = 0
		self.metrics["full_queue_error"] = 0
		self.metrics["put_to_pipeline"] = 0
		self.metrics["pulled_from_pipeline"] = 0
		self.metrics["const_start_time"] = ""
		self.metrics["const_stop_time"] = ""

		self.latency_dict = {}
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
					"{}; full pipeline in fork {} ...".format(
											self.t_name,
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

# CALCULATE LATENCY METRICS
	def calc_time_diff(self,t_a,t_b):
		return t_a - t_b

	def save_timestamp(self,packet):
		r_id = packet.header.request_id
		self.latency_dict[r_id] = time.time()

	def get_latency(self,packet):
		l = None
		r_id = packet.header.request_id
		now = time.time()
		try:
			l = self.calc_time_diff(now,self.latency_dict[r_id])
			del self.latency_dict[r_id]
		except:
			logging.debug("ERROR: could not determine request and recv time for request id: {}".format(r_id))
		latency_dict_keys = list(self.latency_dict.keys())
		for key in latency_dict_keys:
			if self.calc_time_diff(now,self.latency_dict[key]) > self.conf["max_latency_to_accept"]:
				del self.latency_dict[key]
		return l