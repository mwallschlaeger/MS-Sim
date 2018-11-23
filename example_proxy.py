import time, logging, queue, sys, random, threading, signal, os
from listen_network_interface import ListenNetworkInterface
from send_network_interface import SendNetworkInterface
from worker import Worker
from load_balancer import RoundRobinLoadBalancer

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

	# define Interface against IoT devices	
	network_interface1 = ListenNetworkInterface(t_name="IoT_Device_Interface",
					listen_host="localhost",
					listen_port=5090,
					maximum_number_of_listen_clients=10000,
					queque_maxsize=5000
					)

	__,out_iot_inf_pipeline = network_interface1.get_fork(-1)
	in_iot_inf_pipeline = network_interface1.get_after_work_pipeline()

	lb_host_list = [("localhost",5091)]
	round_robin_load_balancer = RoundRobinLoadBalancer(host_list=lb_host_list)
	network_interface2 = SendNetworkInterface(t_name="Compute_Interface",
											load_balancer=round_robin_load_balancer,
											queque_maxsize=5000)

	__,out_compute_inf_pipeline = network_interface2.get_fork(-1)
	in_compute_inf_pipeline = network_interface2.get_after_work_pipeline()

	worker_iot_compute = []
	for i in range(0,5):
		worker_iot_compute.append(Worker(out_iot_inf_pipeline,in_compute_inf_pipeline,proxy_worker_callback,[]))

	worker_compute_iot = []
	for i in range(0,5):
		worker_compute_iot.append(Worker(out_compute_inf_pipeline,in_iot_inf_pipeline,proxy_worker_callback,[]))

	network_interface1.start()
	network_interface2.start()

	for w in worker_iot_compute:
		w.start()	

	for w in worker_compute_iot:
		w.start()	

	input("Press Enter to stop ...")

	#while(RUNNING):
		# main loop
	#	time.sleep(2)

	network_interface1.stop()
	network_interface2.stop()

	for w in worker1:
		w.stop()

	for w in worker2:
		w.stop()


	sys.exit(0)

def proxy_worker_callback(args,msg):
	#logging.debug("{} working ...")
	#for i in range(140):
	#	1.2 * 1.3
	return 0

if __name__ == '__main__':
	main()

