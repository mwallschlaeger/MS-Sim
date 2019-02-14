#!/usr/bin/python3

import argparse, time, logging, queue, sys, random, threading, signal, os
from listen_network_interface import ListenNetworkInterface
from send_network_interface import SendNetworkInterface
from vm import VM
from load_balancer import RoundRobinLoadBalancer
from process import *
import helper

RUNNING = True # controls main loop
ELEMENTS = []
t_name = "MS-AUTHENTICATE"

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
	
	# authentication
	parser.add_argument("-listen_port",type=int, default=5092,help="Port to listen for incoming messages")
	parser.add_argument("-max_clients",type=int,default=5000,help="maximum number of clients connected to authentication")
	parser.add_argument("-queue_size",type=int,default=5000,help="Size of interal processing queue")

	# general 
	parser.add_argument("-cleaning_interval",type=int,default=2,help="interval in which broken connections got cleared")
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

	# define Interface against IoT devices	
	proxy_interface = ListenNetworkInterface(t_name="ProxyInterface",
					listen_host="0.0.0.0",
					listen_port=args.listen_port,
					maximum_number_of_listen_clients=args.max_clients,
					multiprocessing_worker=args.multiprocessing_worker,
					queue_maxsize=args.queue_size
					)
	
	# get pipeline for traffic send to proxy
	out_proxy_pl = proxy_interface.get_send_pipeline()
	
	# get pipeline to worker
	in_proxy_pl = helper.get_queue(multiprocessing_worker=args.multiprocessing_worker,maxsize=args.queue_size)

	# set default workergroup
	proxy_interface.fork_handler.add_fork(pipeline=in_proxy_pl,probability=100)
	
	# initialize all workers
	p = Authentication()
	#p = MemoryCacheOperation()
	for i in range(0,2):
		w = helper.spawn_worker(
			t_name="ProxyToProxyProcess_Worker",
			incoming_pipeline=in_proxy_pl,
			outgoing_pipeline=out_proxy_pl,
			default_process=p,
			multiprocessing_worker=args.multiprocessing_worker)
		ELEMENTS.append(w)
		w.start()

	# start networking
	ELEMENTS.append(proxy_interface)
	proxy_interface.start()

	file_obj = None
	if args.log:
		pass
		#file_obj = open(args.log,"w")
	#helper.log_metrics([proxy_interface,p],print_header=True,file_obj=file_obj)
	while RUNNING:
		proxy_interface.connection_handler.clean(args.cleaning_interval)
		#helper.log_metrics([proxy_interface,p],file_obj=file_obj)
		time.sleep(args.cleaning_interval)

	if args.log:
		pass
		#file_obj.close()
	for e in ELEMENTS:
		e.stop()
	proxy_interface.join()
	sys.exit(0)

if __name__ == '__main__':
	main()