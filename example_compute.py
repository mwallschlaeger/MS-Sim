import time, logging, queue, sys, random, threading, signal, os
from listen_network_interface import ListenNetworkInterface
from worker import Worker

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

	logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

	network1 = ListenNetworkInterface(t_name="test_connection",
					listen_host="localhost",
					listen_port=5091,
					maximum_number_of_listen_clients=10000,
					queque_maxsize=100000
					)
	network1.start()

	__,last_pipeline = network1.get_fork(-1)
	sink_pipeline = network1.get_after_work_pipeline()

	worker = []
	for i in range(0,5):
		worker.append(Worker(last_pipeline,sink_pipeline,compute_worker_callback,[]))

	for w in worker:
		w.start()	

	#while(RUNNING):
		# main loop
	#	time.sleep(2)
	input("Press Enter to stop ...")

	network1.stop()

	for w in worker:
		w.stop()

	sys.exit(0)

def compute_worker_callback(args,msg):
	#logging.debug("{} working ...")
	#for i in range(140):
	#	1.2 * 1.3
	return 0

if __name__ == '__main__':
	main()

