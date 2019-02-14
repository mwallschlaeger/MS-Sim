#!/usr/bin/python3

import argparse, time, logging, queue, sys, random, threading, signal, os
from listen_network_interface import ListenNetworkInterface
from send_network_interface import SendNetworkInterface
from load_balancer import RoundRobinLoadBalancer
from cpu import CPU
from vm import VM
from process import *
from thread_worker import ThreadWorker
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
	parser.add_argument("-multiprocessing_worker",action='store_true',help="enables multiprocessing to improve performance")

	# logging
	parser.add_argument("-log",help="Redirect service quality data to a given file.",metavar='')
	parser.add_argument("-status_log",help="Redirect logs to a given file in addition to the console.",metavar='')
	parser.add_argument("-v",action='store_true',help="Enable verbose logging Sink")
	args = parser.parse_args()

	# manage logging
	debug = False
	if args.v:
		debug = True

	if args.status_log:
		logfile = args.status_log
		helper.configure_logging(debug,logfile)
	else:
		helper.configure_logging(debug)
		logging.debug("debug mode enabled")

	# define Interface against Proxy devices	
	proxy_interface = ListenNetworkInterface(t_name="Proxy_Interface",
					listen_host="0.0.0.0",
					listen_port=args.listen_port,
					maximum_number_of_listen_clients=args.max_clients,
					multiprocessing_worker=args.multiprocessing_worker,
					queue_maxsize=args.queue_size
					)

	# define cloud loadbalancer 
	cloud_lb_host_list = []
	for c in args.cloud_compute:
		cloud_lb_host_list.append((c,args.cloud_compute_port))
	# define Interface against Authenticate devices	
	cloud_load_balancer = RoundRobinLoadBalancer(host_list=cloud_lb_host_list)
	cloud_interface = SendNetworkInterface(t_name="Cloud_Interface",
											load_balancer=cloud_load_balancer,
											multiprocessing_worker=args.multiprocessing_worker,
											queue_maxsize=args.queue_size)

	# validate parameters
	if args.cached_percentile < 0:
		logging.error("{} Negative Percentile for cached response(-cached_percentile).".format(t_name))
		sys.exit(1)
	if args.cached_percentile > 100:
		logging.error("{} Unable to set a Percentile greater 100. (-cached_percentile).".format(t_name))
		sys.exit(1)
	if args.offloading_percentile < 0:
		logging.error("{} Negative Percentile for offloading requests(-offloading_percentile).".format(t_name))
		sys.exit(1)
	if args.offloading_percentile > 100:
		logging.error("{} Unable to set a Percentile greater 100. (-offloading_percentile).".format(t_name))
		sys.exit(1)
	if args.offloading_percentile + args.cached_percentile > 100:
		loggingerror("{}: -cached_percentile + -database_request_percentile exceed 100%".format(t_name))
		sys.exit(1)
	compute_percentile = 100 - args.offloading_percentile - args.cached_percentile

	# get pipeline for traffic to send to Proxy instances
	out_proxy_pl = proxy_interface.get_send_pipeline()

	# get pipeline for traffic to send to Cloud instances
	out_cloud_pl = cloud_interface.get_send_pipeline()

	# create pipeline for cache operation, set fork
	in_iot_cached_pl = helper.get_queue(multiprocessing_worker=args.multiprocessing_worker,maxsize=args.queue_size)
	proxy_interface.fork_handler.add_fork(pipeline=in_iot_cached_pl,probability=args.cached_percentile)

	# create pipeline for offloading operation, set fork
	in_iot_offloading_pl = helper.get_queue(multiprocessing_worker=args.multiprocessing_worker,maxsize=args.queue_size)
	proxy_interface.fork_handler.add_fork(pipeline=in_iot_offloading_pl,probability=args.offloading_percentile)
	
	# create pipeline for local compute operation, set fork
	in_iot_local_compute_pl = helper.get_queue(multiprocessing_worker=args.multiprocessing_worker,maxsize=args.queue_size)
	proxy_interface.fork_handler.add_fork(pipeline=in_iot_local_compute_pl,probability=compute_percentile)

	# create pipeline for receving packets from cloud compute, set fork
	cloud_interface.fork_handler.add_fork(pipeline=out_proxy_pl,probability=100)

	# initialize  workers
	cache_process = MemoryCacheOperation()
	for i in range(0,1):
		w = helper.spawn_worker(
			t_name="CacheProcess_Worker",
			incoming_pipeline=in_iot_cached_pl,
			outgoing_pipeline=out_proxy_pl,
			default_process=cache_process,
			multiprocessing_worker=args.multiprocessing_worker)
		ELEMENTS.append(w)
		w.start()
	
	local_compute_process = LocalCompute()
	for i in range(0,1):
		w = helper.spawn_worker(
			t_name="LocalComputeProcess_Worker",
			incoming_pipeline=in_iot_local_compute_pl,
			outgoing_pipeline=out_proxy_pl,
			default_process=local_compute_process,
			multiprocessing_worker=args.multiprocessing_worker)
		ELEMENTS.append(w)
		w.start()

	offloading_process = Forwarding()
	for i in range(0,1):
		w = helper.spawn_worker(
			t_name="OffloadingProcess_Worker",
			incoming_pipeline=in_iot_offloading_pl,
			outgoing_pipeline=out_cloud_pl,
			default_process=offloading_process,		
			multiprocessing_worker=args.multiprocessing_worker)
		ELEMENTS.append(w)
		w.start()

	# start networking
	ELEMENTS.append(proxy_interface)
	proxy_interface.start()
	ELEMENTS.append(cloud_interface)
	cloud_interface.start()

	#file_obj = None
	if args.log:
		pass
		#file_obj = open(args.log,"w")
	#helper.log_metrics([proxy_interface,cloud_interface,cache_process,offloading_process,local_compute_process,forward_offloading_process],print_header=True,file_obj=file_obj)
	while RUNNING:
		proxy_interface.connection_handler.clean(timeout=1)
		cloud_interface.connection_handler.clean(timeout=1)
		#helper.log_metrics([proxy_interface,cloud_interface,cache_process,offloading_process,local_compute_process,forward_offloading_process],file_obj=file_obj)
		time.sleep(args.cleaning_interval)

	if args.log:
		pass
		#file_obj.close()
	proxy_interface.join()
	cloud_interface.join()
	sys.exit(0)


if __name__ == '__main__':
	main()
