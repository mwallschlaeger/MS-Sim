#!/usr/env/python3

#
# 1% CPU Load generator
# 
import time
import psutil
import threading		


class CPU(threading.Thread):

	def __init__(self,loops,sleeptime=0.0235):
		self.loops=loops
		self.sleeptime=sleeptime
		self.is_running = True
		super().__init__()


	def run(self):
		x = 8
		while self.is_running:
			for i in range(self.loops):
				x*x
			time.sleep(self.sleeptime)

	def get_sleeptime(self):
		return self.sleeptime

	def set_sleeptime(self,sleeptime):
		self.sleeptime = sleeptime

	def stop(self):
		self.is_running = False

class Benchmark(threading.Thread):

	def __init__(self):
		self.l = []
		self.p = psutil.Process()
		self.is_running = True
		super().__init__()
				
	def run(self):
		while(self.is_running):
			self.l.append(self.p.cpu_percent(interval=0.1))


	def get_percentile(self):
		print(self.l)
		return sum(self.l) / float(len(self.l))

	def stop(self):
		self.is_running = False

def do_benchmark():


	percentile = 0.
	n = 1
	inc_value = 0.002
	start_value = 0.05
	duration = 5

	while percentile < 50:
		wait_time = start_value - (inc_value * n)
		cpu = CPU(1000,wait_time)
		benchmark = Benchmark()

		cpu.start()
		benchmark.start()
		time.sleep(duration)
		benchmark.stop()
		cpu.stop()
		percentile = benchmark.get_percentile()
		print(str(float(percentile)))
		n +=1
	return wait_time

def main():

	wait_time = do_benchmark()

	CPU(1000,wait_time).start()

if __name__ == '__main__':
	main()

