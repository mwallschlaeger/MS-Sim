import time

def main():

	import numpy as np
	my_array = np.zeros(4*8192) # create a fixed array length of 8K elements
	my_array += 4 	
	time.sleep(15)

if __name__ == '__main__':
	main()
