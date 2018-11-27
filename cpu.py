import ctypes, time, math, random, os

class CPU():
	
	def __init__(self):
		shared_cpu_lib = os.path.join(os.getcwd(),"libs/utilize_cpu.so")
		self._cpu = ctypes.CDLL(shared_cpu_lib)
		self._cpu.utilize_cpu.argtype = (ctypes.c_int)
		self._cpu.utilize_cpu_sqrt.argtype = (ctypes.c_int)

	def __str__(self):
		return "CPU"

	def c_utilize_cpu(self,loops):
		loops *= 1000
		#array_type = ctypes.c_int * num_numbers
		result = self._cpu.utilize_cpu(ctypes.c_int(loops))
		return int(result)
	
	# loops 100 ~ 25
	def c_utilize_cpu_sqrt(self,loops):
		loops *= 1000
		result = self._cpu.utilize_cpu_sqrt(ctypes.c_int(loops))
		return int(result)

	def py_utilize_cpu_sqrt(self,loops):
		FLT_MAX = 3.402823e+38
		FLT_MIN = 1.175494e-38
		for i in range(loops):
			r = random.uniform(FLT_MIN,FLT_MAX)
			math.sqrt(r*r)
		return 0
