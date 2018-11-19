import time, logging, queue, sys, random, threading
from source import Source
from cpu import CPU

class Worker(threading.Thread):

	# TODO handle central connection list
	# TODO define write pipeline
	def __init__(self,incoming_messages,
				outgoing_messages,
				clb_args,
				clb_func = None,
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
		self.incoming_messages = incoming_messages
		self.outgoing_messages = outgoing_messages

		self.running = True
		super().__init__()

	def __str__(self):
		# TODO may not work properly
		return(super.__str__(self))

	def run(self):
		logging.debug("{} thread started ...".format(self.__str__()))
		while(self.running):
			if not self.incoming_messages.empty():
				try:
					clientsocket, address = self.incoming_messages.get_nowait()
				except Exception as empty:
					continue
				msg=clientsocket.recv(4096)
				logging.debug("Received MSG From {} with content: \n {}".format(address,msg))
				self.clb_func(self.clb_args,msg)
			else: 
				t = random.uniform(self.min_random_wait_to_read,self.max_random_wait_to_read)
				time.sleep(t)

	def stop(self):
		logging.info("Stopping Worker {} ...".format(self.__str__()))
		self.running = False

def main():

	logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

	# instantiate object 
	cpu = CPU()

	pipeline = queue.Queue()
	source = Source(connection_name="test_connection",
					pipeline=pipeline,
					allowed_hosts=None)
	source.start()

	worker = []
	for i in range(0,5):
		worker.append(Worker(pipeline,[],[],example_worker_callback))

	for w in worker:
		w.start()	

	time.sleep(500)


def example_worker_callback(args,msg):
	#logging.debug("{} working ...")
	#for i in range(140):
	#	1.2 * 1.3
	return 0

if __name__ == '__main__':
	main()

