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
t_name = "MS-CLOUD-COMPUTE"

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
	
	# cloud compute
	parser.add_argument("-listen_port",type=int, default=5093,help="Port to listen for incoming messages")
	parser.add_argument("-database",action='append',help="a Database node to interact with",required=True)
	parser.add_argument("-database_port",type=int,default=5094,help="Port the database nodes are listening on")
	parser.add_argument("-max_clients",type=int,default=5000,help="maximum number of clients connected to Cloud Compute")
	parser.add_argument("-queue_size",type=int,default=1000,help="Size of interal processing queue")
	parser.add_argument("-cached_percentile",type=int,default=20,help="Percentile of request answered from cache")
	parser.add_argument("-database_request_percentile",type=int,default=50,help="Percentile of requests further request database (calculated after caching)")

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

	# validate parameters
	if args.cached_percentile < 0:
		logging.error("{} Negative Percentile for cached_percentile requests(-cached_percentile).".format(t_name))
		sys.exit(1)
	if args.cached_percentile > 100:
		logging.error("{} Unable to set a Percentile greater 100. (-cached_percentile).".format(t_name))
		sys.exit(1)
	if args.database_request_percentile < 0:
		logging.error("{} Negative Percentile for database equests(-database_request_percentile).".format(t_name))
		sys.exit(1)
	if args.database_request_percentile > 100:
		logging.error("{} Unable to set a Percentile greater 100. (-cached_percentile).".format(t_name))
		sys.exit(1)
	if args.database_request_percentile + args.cached_percentile > 100:
		logging.error("{}: -cached_percentile + -database_request_percentile exceed 100%".format(t_name))
		sys.exit(1)
	compute_percentile = 100 - args.database_request_percentile- args.cached_percentile

	# define Interface against Proxy devices	
	edge_interface = ListenNetworkInterface(t_name="Edge_Interface",
					listen_host="0.0.0.0",
					listen_port=args.listen_port,
					maximum_number_of_listen_clients=args.max_clients,
					multiprocessing_worker=args.multiprocessing_worker,
					queue_maxsize=args.queue_size
					)
	
	# define cloud loadbalancer 
	database_lb_host_list = []
	for c in args.database:
		database_lb_host_list.append((c,args.database_port))
	# define Interface against Authenticate devices	
	database_load_balancer = RoundRobinLoadBalancer(host_list=database_lb_host_list)
	database_interface = SendNetworkInterface(t_name="Database_Interface",
											load_balancer=database_load_balancer,
											multiprocessing_worker=args.multiprocessing_worker,
											queue_maxsize=args.queue_size)
	# get pipeline for traffic to send to edge
	out_edge_pl = edge_interface.get_send_pipeline()
	# get pipeline for traffic to send to database
	out_databae_pl = database_interface.get_send_pipeline()

	# get pipeline for cache operation
	in_edge_cached_pl = helper.get_queue(multiprocessing_worker=args.multiprocessing_worker,maxsize=args.queue_size) 
	# add cache operation fork
	edge_interface.fork_handler.add_fork(pipeline=in_edge_cached_pl,probability=args.cached_percentile)

	# get pipeline for database requests operations
	in_edge_database_pl = helper.get_queue(multiprocessing_worker=args.multiprocessing_worker,maxsize=args.queue_size)
	# add database request operation fork	
	edge_interface.fork_handler.add_fork(pipeline=in_edge_database_pl,probability=args.database_request_percentile)	

	# get pipeline for compute operations
	in_edge_compute_pl = helper.get_queue(multiprocessing_worker=args.multiprocessing_worker,maxsize=args.queue_size)
	# add compute operation fork	
	edge_interface.fork_handler.add_fork(pipeline=in_edge_compute_pl,probability=compute_percentile)	

	# forward traffic comming from database directly to edge cloud
	database_interface.fork_handler.add_fork(pipeline=out_edge_pl,probability=100)

	print(edge_interface.fork_handler.get_forks())
	
	# initialize  worker
	cache_process = MemoryCacheOperation()
	for i in range(0,1):
		w = helper.spawn_worker(
			t_name="CacheProcess_Worker",
			incoming_pipeline=in_edge_cached_pl,
			outgoing_pipeline=out_edge_pl,
			default_process=cache_process,
			multiprocessing_worker=args.multiprocessing_worker)
		ELEMENTS.append(w)
		w.start()

	database_request_process = Forwarding() # maybe small computation here
	for i in range(0,1):
		w = helper.spawn_worker(
			t_name="DatabaseRequestProcess_Worker",
			incoming_pipeline=in_edge_database_pl,
			outgoing_pipeline=out_databae_pl,
			default_process=database_request_process,
			multiprocessing_worker=args.multiprocessing_worker)
		ELEMENTS.append(w)
		w.start()
	
	compute_process = Compute() 
	for i in range(0,1):
		w = helper.spawn_worker(
			t_name="ComputeProcess_Worker",
			incoming_pipeline=in_edge_compute_pl,
			outgoing_pipeline=out_edge_pl,
			default_process=compute_process,
			multiprocessing_worker=args.multiprocessing_worker)
		ELEMENTS.append(w)
		w.start()

	#database_response_process = ComputeDatabaseResponse() 
	#for i in range(0,1):
	#	w = helper.spawn_worker(
	#		t_name="ComputeDatabaseResponseProcess_Worker",
	#		incoming_pipeline=in_edge_compute_pl,
	#		outgoing_pipeline=out_edge_pl,
	#		default_process=database_response_process,
	#		multiprocessing_worker=args.multiprocessing_worker)
	#	ELEMENTS.append(w)
	#	w.start()

		# start networking
	ELEMENTS.append(edge_interface)
	edge_interface.start()
	ELEMENTS.append(database_interface)
	database_interface.start()


	#file_obj = None
	if args.log:
		pass
		#file_obj = open(args.log,"w")
	#helper.log_metrics([edge_interface,database_interface,cache_process,database_request_process,compute_process,database_response_process],print_header=True,file_obj=file_obj)

	while RUNNING:
		edge_interface.connection_handler.clean(timeout=1)
		database_interface.connection_handler.clean(timeout=1)
		#helper.log_metrics([edge_interface,database_interface,cache_process,database_request_process,compute_process,database_response_process],file_obj=file_obj)
		time.sleep(args.cleaning_interval)

	if args.log:
		pass
	#	file_obj.close()
	edge_interface.join()
	database_interface.join()
	sys.exit(0)

if __name__ == '__main__':
	main()

