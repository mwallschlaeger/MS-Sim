import os
import psutil
import signal
import argparse
import random
import time
import sys
import ctypes
import gc

import importlib.util
spec = importlib.util.spec_from_file_location("stress_ng", "stress-ng/bindings/stress_ng.py")
stress_ng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stress_ng)

STRESS_OPS_PER_LOOP=3
IS_RUNNING = True
CLOSING = False

PROCESS = psutil.Process(os.getpid())
MEGA = 10 ** 6
MEGA_STR = ' ' * MEGA

## HDD ##

WRITTEN_FILES = []

SHARED_LIB_LOCATION = "./readBytes.so"
_flat_read = ctypes.CDLL(SHARED_LIB_LOCATION)

def utilize_hdd_write(filedir,size_in_bytes):
	global WRITTEN_FILES
	filename = str(random.randint(1,99999)) + ".txt"
	filepath = filedir+"/"+filename
	WRITTEN_FILES.append(filepath)
	file_size = round(float(size_in_bytes)) # size in bytes
	with open(filepath, "wb") as f:
		f.write(os.urandom(file_size))
	return filepath

''' build ctypes char array from python string '''
def build_ctypes_char_array(string):
	string = str(string)
	return ctypes.create_string_buffer(bytes(string.encode("ascii")))

_flat_read.readBytes.argstype = ( ctypes.c_int,ctypes.c_void_p())
def flat_hdd_read(read_file,size_in_bytes):
	_flat_read.readBytes(ctypes.c_int(size_in_bytes),build_ctypes_char_array(read_file))

def utilize_hdd_read(read_file,size_in_bytes):
	f = open(read_file, "rb",buffering=0) 
	a = f.read(round(float(size_in_bytes)))
	f.close()
	f = None
	a = None
	gc.collect()
	#	size = 0
	#	c = ""
	#	while size < size_in_bytes:
	#			a = f.readline()
	#			c = a + a
	#		size += len(c)

def delete_files():
	global WRITTEN_FILES
	for f in WRITTEN_FILES:
		os.remove(f)

## CPU | JIFFIES ##

def utilize_cpu(method="nsqrt",max_ops=10):
	stress_ng.stress_cpu(method=method,max_ops=max_ops)

def get_clk_tck():
	import subprocess
	CLK_TCK = int(subprocess.check_output(['getconf', 'CLK_TCK']))
	return CLK_TCK

def get_curr_jiffies(begin_jiffies,CLK_TCK):
	curr_jiffies = get_jiffies(os.getpid(),CLK_TCK)
	diff_jiffies = curr_jiffies - begin_jiffies
	return diff_jiffies

def get_jiffies(pid,CLK_TCK):
	f = open("/proc/{}/stat".format(pid))
	line = f.readline()
	fields = line.split(" ")
	f.close()
	time_sum =  int(fields[13])+int(fields[14])
	return time_sum / float(CLK_TCK)

## MEM ##
def get_current_allocated_memory():
	global PROCESS
	return PROCESS.memory_info()[1]

def allocate_memory(size_in_mb,mem):
	for i in range(size_in_mb):
		try:
			mem.append(MEGA_STR + str(i))
		except MemoryError:
			print("Can not allocate more memory ...")
			break

def free_memory(size_in_mb,mem):
	for i in range(size_in_mb):
		try:
			del mem[0]
		except:
			print("No more memory to free ...")
			break

def manage_memory(target_vms,mem):
	memory_diff = round((get_current_allocated_memory() - target_vms) / MEGA) 
	if memory_diff > 0: ## we have to free memory
		allocate_memory(size_in_mb=memory_diff,mem=mem)
	elif memory_diff < 0: ## we have to allocate
		free_memory(size_in_mb=memory_diff,mem=mem)

## TIME ##

def sleep_diff(begin_time,duration,now):
	past_time = get_diff_time(begin_time,now)
	sleep_time = duration - past_time
	time.sleep(sleep_time)

def get_diff_time(begin_time,now):
	diff_time = float(now - begin_time)
	return diff_time


def wildcard_compare(wildcard_expression, string):
	import fnmatch
	return fnmatch.fnmatch(string.lower(),wildcard_expression.lower())


def utilize_resources(utilization_list,filedir,read_file,proc_key="target"):
	global IS_RUNNING

	CPU_JIFFIES = "proc/"+proc_key+"/cpu-jiffies"
	HDD_WRITE = "proc/"+proc_key+"/disk/writeBytes"
	HDD_READ = "proc/"+proc_key+"/disk/readBytes"
	MEM_VMS = "proc/"+proc_key+"/mem/vms"

	CLK_TCK = get_clk_tck()
	begin_jiffies = -1
	memory_allocation_list = []

	while IS_RUNNING:
		for e in utilization_list:
			begin_time = time.time()
			begin_jiffies = get_jiffies(os.getpid(),CLK_TCK)

			if not IS_RUNNING:
				break
			round_duration = float(round((e["duration"] * 10))/ 10)
			if round_duration < 1:
				target_jiffies = float(e[CPU_JIFFIES]) * round_duration
			else: 
				target_jiffies = float(e[CPU_JIFFIES]) / round_duration 


			target_hdd_write = float(e[HDD_WRITE])
			target_hdd_read = float(e[HDD_READ])
			target_vms = float(e[MEM_VMS])
			target_duration = e["duration"]
			
			time_exeed = False
			jiffies_exeed = False

			# hDD
			wf = utilize_hdd_write(filedir=filedir,size_in_bytes=target_hdd_write)
			utilize_hdd_read(read_file=read_file,size_in_bytes=target_hdd_read)

			# mem
			manage_memory(target_vms,memory_allocation_list)

			# jiffies
			while not time_exeed and not jiffies_exeed:
				if get_curr_jiffies(begin_jiffies,CLK_TCK) > target_jiffies:
					jiffies_exeed = True
					sleep_diff(begin_time=begin_time,duration=target_duration,now=time.time())
					break
				if get_diff_time(begin_time,time.time()) > target_duration:
					time_exeed = True
					print("TIME")
					break
				utilize_cpu()
			print("TIME: diff: {}".format(begin_time + target_duration - time.time()))
			print("JIFFIES: target:{:.3f}, current: {:.3f}".format(target_jiffies,get_curr_jiffies(begin_jiffies,CLK_TCK)))
			print("HDD_WRITE: target:{:.3f}, current: {:.3f}".format(target_hdd_write,os.path.getsize(wf)))
			#print("HDD_READ: target:{:.3f}, current: {:.3f}".format(target_hdd_read,rf))
		break
	delete_files()

def parse_csv_to_dict_list(csv_file,proc_key="target"):

	CPU_JIFFIES = "proc/"+proc_key+"/cpu-jiffies"
	HDD_WRITE = "proc/"+proc_key+"/disk/writeBytes"
	HDD_READ = "proc/"+proc_key+"/disk/readBytes"
	MEM_VMS = "proc/"+proc_key+"/mem/vms"

	from bitflow.marshaller import CsvMarshaller
	csv_marshaller = CsvMarshaller()

	header = None

	values = []
	previous_sample = None

	with open(csv_file) as f:
		import numpy as np
		for line in f:
			if not header:
				header = csv_marshaller.unmarshall_header(header_line=line)
			else:	
				sample = csv_marshaller.unmarshall_sample(header=header,metrics_line=line)
				if previous_sample:
					e = {CPU_JIFFIES : sample.get_metricvalue_by_name(CPU_JIFFIES),
						HDD_WRITE : sample.get_metricvalue_by_name(HDD_WRITE),
						HDD_READ : sample.get_metricvalue_by_name(HDD_READ),
						MEM_VMS : sample.get_metricvalue_by_name(MEM_VMS),
						"duration" : (sample.get_timestamp() - previous_sample.get_timestamp()) / np.timedelta64(1, 's')} # in seonds
					values.append(e)
					previous_sample = sample
				else:
					previous_sample = sample

	return values
