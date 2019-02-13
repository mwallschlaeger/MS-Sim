#!/usr/bin/python3

import argparse, time, logging, queue, sys, random, threading, signal, os
from listen_network_interface import ListenNetworkInterface
from send_network_interface import SendNetworkInterface
from load_balancer import RoundRobinLoadBalancer
from cpu import CPU
from vm import VM
from process import Process, ForwardingProcess
from worker import Worker
import helper

RUNNING = True # controls main loop
ELEMENTS = []
t_name = "MS-COMPUTE"


def sig_int_handler(signal, frame):

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
	
	# compute
	parser.add_argument("-listen_port",type=int, default=5091,help="Port to listen for incoming messages")
	parser.add_argument("-cloud_compute",action='append',help="a Cloud-Compute node to interact with",required=True)
	parser.add_argument("-cloud_compute_port",type=int,default=5093,help="Port the Cloud-Compute nodes are listening on")
	parser.add_argument("-max_clients",type=int,default=5000,help="maximum number of clients connected to compute")
	parser.add_argument("-queue_size",type=int,default=5000,help="Size of interal processing queue")
	parser.add_argument("-offloading_percentile",type=int,default=50,help="Percentil of request offloaded to central cloud")
	parser.add_argument("-cached_percentile",type=int,default=20,help="Percentil of request answered from cache to central cloud(calculated after offloading)")

	# general 
	parser.add_argument("-cleaning_interval",type=int,default=2,help="interval in which broken connections got cleared",metavar='2')

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
		helper.configure_logging(debug,logfile)
	else:
		helper.configure_logging(debug)
		logging.debug("debug mode enabled")

# 1. IoT devices send data to Proxy
# (2. Proxy asks Authenticate for authentification) only some %
# 3. Proxy forwards request to Compute
# 4. a. Compute offloads into Cloud
#    b. Compute computes locally 
#    c. Compute answers with cached data 
#
#		|					*EDGE_CLOUD *					|				* PUBLIC CLOUD *
#		|					*************					|				****************
#		|		   	   #####################				|
#		|		  	  /# 5092 AUTHENTICATE #				|4.a  ######################\
# IoT--	|			2/ #####################			  --------# 5093 Cloud Compute # \
#     |	|			/									 /	|	  ######################  \
# IoT------##############				################/	|4.a  ######################   \#################
#	  1 |  # 5090 PROXY #---------------# 5091 Compute #----------# 5093 Cloud Compute #----# 5094 Database #
# IoT------##############   \   3   /	################\	|	  ######################   /#################
#		|		   		 	 -------				     \	|4.a  ######################  /
# IoT------##############   /  3    \	################  --------# 5093 Cloud Compute # /		
#	  1 |  # 5090 PROXY #---------------# 5091 COMPUTE #	|	  ######################/
# IoT------##############				################	|
#															|
#															|

	# define Interface against Proxy devices	
	proxy_interface = ListenNetworkInterface(t_name="Proxy_Interface",
					listen_host="0.0.0.0",
					listen_port=args.listen_port,
					maximum_number_of_listen_clients=args.max_clients,
					queque_maxsize=args.queue_size
					)

	# define cloud loadbalancer 
	cloud_lb_host_list = []
	for c in args.cloud_compute:
		cloud_lb_host_list.append((c,args.cloud_compute_port))
	# define Interface against Authenticate devices	
	cloud_load_balancer = RoundRobinLoadBalancer(host_list=cloud_lb_host_list)
	cloud_interface = SendNetworkInterface(t_name="Authenticate_Interface",
											load_balancer=cloud_load_balancer,
											queque_maxsize=args.queue_size)

	# get pipeline for incoming traffic from Proxy to answer from cache
	if args.cached_percentile < 0:
		logging.error("{} Negative Percentile for cached response(-cached_percentile).".format(t_name))
		sys.exit(1)
	if args.cached_percentile > 100:
		logging,error("{} Unable to set a Percentile greater 100. (-cached_percentile).".format(t_name))
		sys.exit(1)
	in_iot_cached_pl = queue.Queue(maxsize=args.queue_size) # maybe define helper function
	proxy_interface.fork_handler.add_fork(pipeline=in_iot_cached_pl,probability=args.cached_percentile,pos=0)

	# get pipeline for incoming traffic from Proxy to offload
	if args.offloading_percentile < 0:
		logging.error("{} Negative Percentile for offloading requests(-offloading_percentile).".format(t_name))
		sys.exit(1)
	if args.offloading_percentile > 100:
		logging,error("{} Unable to set a Percentile greater 100. (-offloading_percentile).".format(t_name))
		sys.exit(1)
	in_iot_offloading_pl = queue.Queue(maxsize=args.queue_size) # maybe define helper function
	proxy_interface.fork_handler.add_fork(pipeline=in_iot_offloading_pl,probability=args.offloading_percentile,pos=0)
	
	# get pipeline for incoming traffic from Proxy to local compute
	__,in_iot_local_compute = proxy_interface.fork_handler.get_fork(-1)

	# get pipeline for incoming traffic from Proxy
	__,in_iot_local_compute = proxy_interface.fork_handler.get_fork(-1)

	# get pipeline for traffic to send to Proxy instances
	out_proxy_pl = proxy_interface.get_after_work_pipeline()

	# get pipeline for traffic to send to Cloud instances
	out_cloud_pl = cloud_interface.get_after_work_pipeline()

	# initialize  workers
	cache_process = CacheProcess()
	for i in range(0,1):
		w = Worker(
			t_name="CacheProcess_Worker",
			incoming_pipeline=in_iot_cached_pl,
			outgoing_pipeline=out_proxy_pl,
			process=cache_process)
		ELEMENTS.append(w)
		w.start()
	
	offloading_process = ForwardingProcess()
	for i in range(0,2):
		w = Worker(
			t_name="OffloadingProcess_Worker",
			incoming_pipeline=in_iot_offloading_pl,
			outgoing_pipeline=out_cloud_pl,
			process=offloading_process)
		ELEMENTS.append(w)
		w.start()
	
	local_compute_process = LocalComputeProcess()
	for i in range(0,3):
		w = Worker(
			t_name="LocalComputeProcess_Worker",
			incoming_pipeline=in_iot_local_compute,
			outgoing_pipeline=out_proxy_pl,
			process=local_compute_process)
		ELEMENTS.append(w)
		w.start()

	forward_offloading_process = ForwardingProcess()
	for i in range(0,1):
		w = Worker(
			t_name="ForwardOffloadingProcess_Worker",
			incoming_pipeline=in_iot_local_compute,
			outgoing_pipeline=out_proxy_pl,
			process=forward_offloading_process)
		ELEMENTS.append(w)
		w.start()

	# start networking
	ELEMENTS.append(proxy_interface)
	proxy_interface.start()
	ELEMENTS.append(cloud_interface)
	cloud_interface.start()

	while RUNNING:
		proxy_interface.connection_handler.clean(timeout=1)
		cloud_interface.connection_handler.clean(timeout=1)
		time.sleep(args.cleaning_interval)

	proxy_interface.join()
	cloud_interface.join()
	sys.exit(0)

class CacheProcess(Process):

	def __init__(self):
		super().__init__()
		self.t_name = "CacheProcess"

		vm_bytes=1024*2000
		self.vm = VM(method="zero-one",vm_bytes=vm_bytes)
		self.children["VM"]=self.vm

	def execute(self,device_id,request_id):
		self.vm.utilize_vm()


class LocalComputeProcess(Process):

	def __init__(self):
		super().__init__()
		self.t_name = "LocalComputeProcess"
		self.cpu = CPU(method="nsqrt",max_ops=5)
		self.children["CPU"]=self.cpu

	def execute(self,device_id,request_id):
		self.cpu.utilize_cpu()


if __name__ == '__main__':
	main()