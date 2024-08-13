/* 32-tap FIR filter processing 1 point */
/* Modified to use arrays - SMP */

//#include "traps.h"

#include<iostream>

using namespace std;

#define SIZE 10000

int kernel(double **A, int N, double Tol, int *P);

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

  kernel(A, N, 0.001, P);

  return 0;
}

int kernel(double **A, int N, double Tol, int *P) {

    int i, j, k, imax;

    for (i = 0; i <= N; i+=2) {
        P[i] = i; //Unit permutation matrix, P[N] initialized with N
        P[i+1] = i+1; //Unit permutation matrix, P[N] initialized with N
//        P[i+2] = i+2; //Unit permutation matrix, P[N] initialized with N
//        P[i+3] = i+3; //Unit permutation matrix, P[N] initialized with N
    }
    return 1;
}

