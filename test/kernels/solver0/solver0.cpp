/* 32-tap FIR filter processing 1 point */
/* Modified to use arrays - SMP */

//#include "traps.h"

#include<iostream>

using namespace std;

#define SIZE 10000

void kernel(double **A, int *P, double *b, int N, double *x); 

int main()
{

  int N = 2;
  double **A = new double*[N];
  int *P = new int[N+1];
  double *x = new double[N];
  double *b = new double[N];
  double **IA = new double*[N];

  for(int i=0; i<N; ++i) {
    A[i] = new double[N];
    IA[i] = new double[N];
  }

  A[0][0] = 4;
  A[0][1] = 3;
  A[1][0] = 6;
  A[1][1] = 3;

  b[0] = 10;
  b[1] = 12;

  kernel(A, P, b, N, x);

  return 0;
}

void kernel(double **A, int *P, double *b, int N, double *x) {

  int bound = N*N;
  for(int index=0; index<bound; ++index) {
    int i = index / N;
    int k = index % N;

    if(k == 0) {
      x[i] = b[P[i]];
    }
    if(k < i) {
      x[i] -= A[i][k] * x[k];
    }

  }

/*
    for (int i = 0; i < N; i++) {
        x[i] = b[P[i]];

        for (int k = 0; k < i; k++)
            x[i] -= A[i][k] * x[k];
    }
*/
}

