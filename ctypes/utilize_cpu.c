#include <math.h>
#include <complex.h>
#include <stdlib.h>

//#define RAND_MAX 3.402823e+38
#define FLT_MIN 1.175494e-38
#define FLT_MAX 3.402823e+38

// source for additional implementations
// https://github.com/ColinIanKing/stress-ng/blob/master/stress-cpu.c

int utilize_cpu(int loops) {
    float a = 1.23456;
    float b = 3.45567;
    int j = 0;
    double c = 0;
    for (int i = 0; i < loops; i++) {
        c = a * b * a / b - b * a * c;
        c = a * b * a / b - b * a;
        j++;
    }
    return j;
}

double rand_float( double low, double high ) {
    return ( ( double )rand() * ( high - low ) ) / ( double )RAND_MAX + low;
}

int utilize_cpu_sqrt(int loops) {
	int i;

	for (i = 0; i < loops; i++) {
		double rnd = rand_float(FLT_MIN,FLT_MAX);
		double r = sqrt((double)rnd) * sqrt((double)rnd);
	}
	return 0;
}
