/* 32-tap FIR filter processing 1 point */
/* Modified to use arrays - SMP */

//#include "traps.h"

#include<iostream>

using namespace std;

#define SIZE 10000

double kernel(double **A, int *P, int N);

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

  kernel(A, P, N);

  return 0;
}

double kernel(double **A, int *P, int N) {

    double det = A[0][0];

    for (int i = 1; i < N; i+=1) {
      det *= A[i][i];
      if(i == N-1) {
        if((P[N] - N) % 2 != 0) {
          det = -det;
        }
      }
    }
    return det;
//    return (P[N] - N) % 2 == 0 ? det : -det;

}

