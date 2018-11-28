#!/usr/bin/python3

import argparse, time, logging, queue, sys, random, threading, signal, os
from listen_network_interface import ListenNetworkInterface
from cpu import CPU
from process import Process
from worker import Worker

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

	# define Interface against Proxy devices	
	proxy_interface = ListenNetworkInterface(t_name="Proxy_Interface",
					listen_host="0.0.0.0",
					listen_port=args.listen_port,
					maximum_number_of_listen_clients=args.max_clients,
					queque_maxsize=args.queue_size
					)
	
	# get pipeline for incoming traffic
	__,out_proxy_inf_pipeline = proxy_interface.get_fork(-1)

	# get pipeline for traffic to send to Proxy instances
	in_proxy_inf_pipeline = proxy_interface.get_after_work_pipeline()

	ELEMENTS.append(proxy_interface)
	proxy_interface.start()

	for i in range(0,5):
		w = Worker(out_proxy_inf_pipeline,
					in_proxy_inf_pipeline,
					ComputeProcess()
					)
		ELEMENTS.append(w)
		w.start()

	proxy_interface.join()
	sys.exit(0)

class ComputeProcess(Process):

	def __init__(self):
		self.cpu = CPU()
		Process().__init__()

	def __str__(self):
		return "ComputeProcess"

	def execute(self,device_id,request_id):
		self.cpu.c_utilize_cpu_sqrt(5)


if __name__ == '__main__':
	main()