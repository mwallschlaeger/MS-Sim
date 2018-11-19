import time,random

class CPU():
	class __CPU():

		def __init__(self,loops,factor,diversity):
			self.loops = loops
			self.factor = factor
			self.diversity = diversity

		def anomaly_loop_drift_per_minute(self, drift_per_min):
			""" increases the number of  loops per minute """
			pass

		def anomaly_loop_drift_per_hour(self, drift_per_min):
			""" increases the number of  loops per hour """
			pass

		def __get_loops(self):
			plus_minus = random.randint(1,2)
			variation = random.randint(0,self.diversity)
			if(plus_minus == 1):
				variation *= -1
			return variation
		
		def __default_CPU(self,loops,factor):
			for i in range(self.__get_loops()):
				self.factor*self.factor

		def very_low_CPU():
			self.__default_CPU(self.loops,self.factor)
			
		def low_CPU(self):
			very_low_CPU()
			very_low_CPU()

		def medium_CPU(self):
			low_CPU()
			low_CPU()


		def high_CPU(self):
			medium_CPU()
			medium_CPU()

		def very_high_CPU(self):
			high_CPU()
			high_CPU()

		def manual_CPU(self,loops,factor):
			self.__default_CPU(loops,factor)

		def __str__(self):
			return repr(self) + self.val
	    

	instance = None
	def __init__(self, loops=20,factor=8,diversity=3):
		if not CPU.instance:
			CPU.instance = CPU.__CPU(loops,factor,diversity)
		
	def __getattr__(self, name):
		return getattr(self.instance, name)



	