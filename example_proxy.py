import time, logging, queue, sys, random, threading, signal, os
from listen_network import ListenNetwork
from cpu import CPU

class Worker(threading.Thread):

	def __init__(self,
				ingoing_pipeline,
				outgoing_pipeline,
				clb_func = None, # a function executed on each element of the ingoing pipeline
				clb_args = [], # list of parameters for clb func
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
		self.clb_func = clb_func
		self.clb_args = clb_args
		self.ingoing_pipeline = ingoing_pipeline
		self.outgoing_pipeline = outgoing_pipeline

		self.running = True
		super().__init__()

	def __str__(self):
		# TODO may not work properly
		return(super.__str__(self))

	def run(self):
		logging.debug("{} thread started ...".format(self.__str__()))
		while(self.running):
			device_id,request_id = self.ingoing_pipeline.get()
			self.clb_func(self.clb_args,[device_id,request_id])
			self.outgoing_pipeline.put((device_id,request_id),timeout=0.1)
 

	def stop(self):
		logging.info("Stopping Worker {} ...".format(self.__str__()))
		self.running = False



def sig_int_handler(signal, frame):
	# TODO somehow not closing everything properly

	logging.info("User defined process stop ....")
	global RUNNING
	if RUNNING == False:
		os.kill(signal.CTRL_C_EVENT, 0)
	RUNNING = False


RUNNING = True # controls main loop

def main():
	#ssignal.signal(signal.SIGINT, sig_int_handler)

	logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

	network1 = ListenNetwork(t_name="test_connection",
					listen_host="localhost",
					listen_port=5090,
					maximum_number_of_listen_clients=10000,
					queque_maxsize=100000
					)
	network1.start()

	__,last_pipeline = network1.get_fork(-1)
	sink_pipeline = network1.get_after_work_pipeline()

	worker = []
	for i in range(0,5):
		worker.append(Worker(last_pipeline,sink_pipeline,example_worker_callback,[]))

	for w in worker:
		w.start()	

	while(RUNNING):
		# main loop
		time.sleep(2)

	network1.stop()

	for w in worker:
		w.stop()

	sys.exit(0)

def example_worker_callback(args,msg):
	#logging.debug("{} working ...")
	#for i in range(140):
	#	1.2 * 1.3
	return 0

if __name__ == '__main__':
	main()

