#!/usr/bin/python3

import argparse, time, logging, queue, sys, random, threading, signal, os
from listen_network_interface import ListenNetworkInterface
from send_network_interface import SendNetworkInterface
from worker import Worker
from load_balancer import RoundRobinLoadBalancer
from process import Process

RUNNING = True # controls main loop
ELEMENTS = []

def configure_logging(debug,filename=None):
	if filename is None:
		if debug:
			logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)
		else:
			logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
	else:
		if debug:
			logging.basicConfig(filename=filename,format='%(asctime)s %(message)s', level=logging.DEBUG)
		else:
			logging.basicConfig(filename=filename,format='%(asctime)s %(message)s', level=logging.INFO)

def sig_int_handler(signal, frame):
	# TODO somehow not closing everything properly

	global RUNNING
	global ELEMENTS

	if RUNNING == False:
		os.kill(signal.CTRL_C_EVENT, 0)
		
	RUNNING = False
	for e in ELEMENTS:
		e.stop()
	
def main():
	global ELEMENTS
	signal.signal(signal.SIGINT, sig_int_handler)

	parser = argparse.ArgumentParser()
	
	# proxy
	parser.add_argument("-listen_port",type=int, default=5090,help="Port to listen for incoming messages")
	parser.add_argument("-compute",action='append',help="a Compute node to interact with",required=True)
	parser.add_argument("-compute_port",type=int,default=5091,help="Port the compute nodes are listening on")
	parser.add_argument("-max_clients",type=int,default=5000,help="maximum number of clients connected to proxy")
	parser.add_argument("-queue_size",type=int,default=5000,help="Size of interal processing queue")

	# logging
	parser.add_argument("-log",help="Redirect logs to a given file in addition to the console.",metavar='')
	parser.add_argument("-v",action='store_true',help="Enable verbose logging Sink")
	args = parser.parse_args()

	# manage logging
	debug = False
	if args.v:
		debug = True

	if args.log:
		logfile = args.log
		configure_logging(debug,logfile)
	else:
		configure_logging(debug)
		logging.debug("debug mode enabled")

	# define Interface against IoT devices	
	network_interface1 = ListenNetworkInterface(t_name="IoT_Device_Interface",
					listen_host="0.0.0.0",
					listen_port=args.listen_port,
					maximum_number_of_listen_clients=args.max_clients,
					queque_maxsize=args.queue_size
					)

	# get pipeline for incoming traffic
	__,out_iot_inf_pipeline = network_interface1.get_fork(-1)
	
	# get pipeline for traffic to send to IoT devices
	in_iot_inf_pipeline = network_interface1.get_after_work_pipeline()

	# define loadbalancer 
	lb_host_list = []
	for c in args.compute:
		lb_host_list.append((c,args.compute_port))
	round_robin_load_balancer = RoundRobinLoadBalancer(host_list=lb_host_list)
	
	# define Interface against Compute nodes
	network_interface2 = SendNetworkInterface(t_name="Compute_Interface",
											load_balancer=round_robin_load_balancer,
											queque_maxsize=args.queue_size)

	# get pipeline for traffic come from compute instances
	__,out_compute_inf_pipeline = network_interface2.get_fork(-1)
	# get pipeline for traffic to send to Compute instances
	in_compute_inf_pipeline = network_interface2.get_after_work_pipeline()

	# initialize all workers
	proxy_to_comp = ProxyToCOmputeProcess()
	for i in range(0,5):
		w = Worker(
			out_iot_inf_pipeline,
			in_compute_inf_pipeline,
			proxy_to_comp)
		ELEMENTS.append(w)
		w.start()

	comp_to_proxy = ComputeToProxyProcess()
	for i in range(0,5):
		w = Worker(
			out_compute_inf_pipeline,
			in_iot_inf_pipeline,
			comp_to_proxy
			)
		ELEMENTS.append(w)
		w.start()

	# start networking
	ELEMENTS.append(network_interface1)
	network_interface1.start()
	ELEMENTS.append(network_interface2)
	network_interface2.start()

	while RUNNING:
		network_interface1.clean(1)
		network_interface2.clean(1)
		time.sleep(2)

	network_interface2.join()
	network_interface1.join()

	sys.exit(0)


class ComputeToProxyProcess(Process):

	def __init__(self):
		Process().__init__()

	def __str__(self):
		return "ProxyToCOmputeProcess"

	def execute(self,device_id,request_id):
		pass 

class ProxyToCOmputeProcess(Process):

	def __init__(self):
		Process().__init__()

	def __str__(self):
		return "ProxyToCOmputeProcess"

	def execute(self,device_id,request_id):
		pass


if __name__ == '__main__':
	main()

