#!/usr/bin/env python

import argparse, yaml, signal, sys, os, logging
from pprint import pprint, pformat
import process
import helper

RUNNING = True # controls main loop
ELEMENTS = []

SERVICE_DICT = {
			"name":{
				"default":"MS-Database",
				"required":True,
				"description":"Service Name",
				"type":str
				},
			"multiprocessing":{
				"default":True,
				"required":False,
				"description":"enables Multiprocessing Workers, uses more than one CPU core (True|False)",
				"type":bool
				},
			"listen":{
				"default":{},
				"required":True,
				"description":"Listen dict entry ...",
				"type":dict
				},
			"pipelines":{
				"default":{},
				"required":True,
				"description":"Pipelines dict entry ...",
				"type":dict
				},
			"outputs":{
				"default":{},
				"required":False,
				"description":"Pipelines dict entry ...",
				"type":dict
				},
			"queue_maxsize":{
				"default":500,
				"required":False,
				"description":"Maximum number of requests in queue to process",
				"type":int
				}
			}

LISTEN_DICT = {
			"host":{
				"default":"localhost",
				"required":True,
				"description":"Host to listen on",
				"type":str
				},
			"port":{
				"default":"5090",
				"required":True,
				"description":"Port to listen on",
				"type":int
				},
			"max_clients":{
				"default":500,
				"required":False,
				"description":"Number of maximum clients allowed to connect at a time",
				"type":int
				},
			"queue_maxsize":{
				"default":SERVICE_DICT["queue_maxsize"]["default"],
				"required":False,
				"description":"Maximum number of requests in queue to process",
				"type":int
				},
			}

PIPELINE_DICT = {
			"worker":{
				"default":"1",
				"required":False,
				"description":"Number of workers or threads spawned for this Pipeline",
				"type":int
				},
			"processes":{
				"default":[],
				"required":True,
				"description":"Processes List. Defines different processes available in this pipeline",
				"type":list
				},
			"probability":{
				"default":"100",
				"required":True,
				"description":"Probability to execute this pipeline",
				"type":int
				},
		    "output":{
		    	"default":"response",
				"required":True,
				"description":"output of pipeline. response || name of output",
				"type":str
			    }
			}

OUTPUT_DICT = {
			"hosts":{
				"default":[],
				"required":True,
				"description":"Hosts to send to",
				"type":list
				},
			"port":{
				"default":"5090",
				"required":True,
				"description":"Port of hosts to send to",
				"type":int
				},
			"response":{
				"default":"response",
				"required":False,
				"description":"how to handle responses to a send request ( response || ouput)",
				"type":str
				},
			"queue_maxsize":{
				"default":SERVICE_DICT["queue_maxsize"]["default"],
				"required":False,
				"description":"Maximum number of requests in queue to process",
				"type":int
				}
			}

def sig_int_handler(signal, frame):
	global RUNNING
	global ELEMENTS

	if RUNNING == False:
		os.kill(signal.CTRL_C_EVENT, 0)
		
	RUNNING = False
	for e in ELEMENTS:
		e.stop()

def exit_err(error_msgs=[]):
	for em in error_msgs:
		logging.error("ERROR: "+ em)
	sys.exit(1)

def type_check(keyword,v_type):
	if v_type is bool:
		try:
			keyword = bool(keyword)
		except: 
			return False

	if type(keyword) is v_type: # typecheck
		return True
	return False

def parse_leaf(leaf,leaf_name,p_dict):
	n_leaf = {}
	for keyword,v in p_dict.items():
		missing_line = "Missing Value {} in {} ...".format(keyword,leaf_name)
		type_err_line ="Incorrect type for {}, type: {} is required.".format(keyword,str(v["type"]))
		description_line = "Description: {}".format(v["description"])
		default_line ="Default: {}".format(v["default"])
		
		if keyword in leaf: # if keyword exists in yaml
			if type_check(leaf[keyword],v["type"]): # typecheck
				n_leaf[keyword]=leaf[keyword]
			else:
				exit_err([type_err_line])
		else: # if keyword is not set
			if v["required"] is True: # if required but does not exist
				exit_err([missing_line,description_line,default_line])
			else: # not required and not existing, set default
				n_leaf[keyword]=v["default"]
	return n_leaf

def parse_yaml(yaml_object):
	global ELEMENTS

	if "service" in yaml_object:
		service = yaml_object["service"] 
	else: 
		exit_err(["Missing \"service\" entry at the root of the yaml file"])
	s_dict = parse_leaf(leaf=service,leaf_name="service",p_dict=SERVICE_DICT)
	logging.debug("Listen:\n "+pformat(s_dict,indent=1,depth=8,width=160))

	# LISTEN
	l_dict={}
	if "listen" in s_dict:
		listen = s_dict["listen"] 
	else: 
		exit_err(["Missing \"listen\" entry at service leaf of the yaml file"])
	l_dict = parse_leaf(leaf=listen,leaf_name="listen",p_dict=LISTEN_DICT)
	logging.debug("Listen:\n "+pformat(l_dict,indent=1,depth=8,width=160))

	#OUTPUT
	o_dict = {}
	if "outputs" in s_dict:
		outputs = s_dict["outputs"]
		for k,v in outputs.items():
			o_dict[k] = parse_leaf(leaf=v,leaf_name="outputs",p_dict=OUTPUT_DICT)
			logging.debug("Output ({}):\n ".format(k)+pformat(o_dict[k],indent=1,depth=8,width=160))

	# PIPELINES
	p_dict = {}
	if "pipelines" in s_dict:
		pipelines = s_dict["pipelines"] 
	else: 
		exit_err(["Missing \"pipelines\" entry at service leaf of the yaml file"])
	for k,v in pipelines.items():
		p_dict[k] = parse_leaf(leaf=v,leaf_name="pipeline",p_dict=PIPELINE_DICT)
	
		# check crosswise dependencies
		if v["output"] == "response":
			pass
		elif v["output"] not in  o_dict.keys():
				exit_err(["undefinded Output ({}) in pipeline {} ...".format(v["output"],k)])	
		logging.debug("Pipeline ({}):\n ".format(k)+pformat(p_dict[k],indent=1,depth=8,width=160))

	return s_dict,l_dict,p_dict,o_dict

def build_structure(service_dict,listen_dict,pipeline_dict,output_dict):
	global ELEMENTS
	# build listen interface
	from listen_network_interface import ListenNetworkInterface
	listen_dict["instance"] = ListenNetworkInterface(
			t_name=service_dict["name"]+"_interface",
			listen_host=listen_dict["host"],
			listen_port=listen_dict["port"],
			maximum_number_of_listen_clients=listen_dict["max_clients"],
			queue_maxsize=listen_dict["queue_maxsize"]
			)
	ELEMENTS.append(listen_dict["instance"])

	# build output interface(s)
	from load_balancer import RoundRobinLoadBalancer
	from send_network_interface import SendNetworkInterface
	for k,v in output_dict.items():
		# define Interface 
		load_balancer = RoundRobinLoadBalancer(host_list=[(h,v["port"]) for h in v["hosts"]])
		output_dict[k]["instance"] = SendNetworkInterface(t_name=k+"_Interface",
											load_balancer=load_balancer,
											multiprocessing_worker=service_dict["multiprocessing"],
											queue_maxsize=v["queue_maxsize"])
		ELEMENTS.append(output_dict[k]["instance"])

	# build Worker and Processes
	for k,v in pipeline_dict.items():
		pipeline_dict[k]["instances"]=[]
		# setup pipelines
		pl = helper.get_queue(multiprocessing_worker=service_dict["multiprocessing"],maxsize=listen_dict["queue_maxsize"])
		# add to fork.handler
		if not listen_dict["instance"].fork_handler.add_fork(pipeline=pl,probability=v["probability"]):
			exit_err(["could not bind {} to ListenInterface (ForkHandler), wrong probabilities ...".format(k)])
		# spawn_worker
		for i in range(v["worker"]):
			#keyword check
			if v["output"] == "response":
				out_pl = listen_dict["instance"].get_send_pipeline()			
			else:
				out_pl = output_dict[v["output"]]["instance"].get_send_pipeline()

			# prepare process
			p_default = None 
			processes = []
			for p in v["processes"]: 
				p_name=(list(p.keys())[0])
				p_type=p[p_name]
				p_class = process.get_process_by_name(p_name)
				if p_class == None:
					exit_err(["{} is not a valid Process ...".format(p_name),"Use one of: {}".format(process.get_process_list())])
				if p_type == "default":
					p_default  = p_type
				else: 
					processes.append((p_class(),p_type))

			if p_default == None:
				exit_err(["No default process type set for process: {}...".format(k)])

			# build process
			worker = helper.spawn_worker(
				t_name=k+"_worker",
				incoming_pipeline=pl,
				outgoing_pipeline=out_pl,
				default_process=p_default,
				multiprocessing_worker=service_dict["multiprocessing"])
			for p_name,p_type in processes:
				worker.add_process(p_name,p_type)
			pipeline_dict[k]["instances"].append(worker)
			ELEMENTS.append(worker)



def main():
	global ELEMENTS
	signal.signal(signal.SIGINT, sig_int_handler)

	parser = argparse.ArgumentParser()
	#general
	parser.add_argument("--yaml","-y",type=str,required=True,help="MS Yaml file to parse")
	parser.add_argument("--print","-p",action='store_true',help="prints yaml in the beginning, (will also be written into logs")
	# logging
	parser.add_argument("-log",help="Redirect logs to a given file in addition to the console.",metavar='')
	parser.add_argument("-v",action='store_true',help="Enable verbose logging Sink")

	args = parser.parse_args()

	debug = False
	if args.v:
		debug = True

	if args.log:
		logfile = args.log
		helper.configure_logging(debug,logfile)
	else:
		helper.configure_logging(debug)
		logging.debug("debug mode enabled")

	try:
		stream = open(args.yaml, 'r')
		yaml_object = yaml.load(stream)
	except:
		logging.error("{} file does not exists ...".format(args.yaml))
		sys.exit(1)

	if args.print:
		logging.info("Input FIle:\n "+pformat(yaml_object,indent=1,depth=8,width=160))
	

	s_dict,l_dict,p_dict,o_dict = parse_yaml(yaml_object=yaml_object)	
	build_structure(service_dict=s_dict,
					listen_dict=l_dict,
					pipeline_dict=p_dict,
					output_dict=o_dict)

	# start worker 
	for k,v in p_dict.items():
		for instance in v["instances"]:
			instance.start()

	# start send interface
	for k,__ in o_dict.items():
			o_dict[k]["instance"].start()

	# start listen interface
	l_dict["instance"].start()

if __name__ == '__main__':
	main()