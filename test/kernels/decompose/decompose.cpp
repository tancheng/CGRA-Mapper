/* 32-tap FIR filter processing 1 point */
/* Modified to use arrays - SMP */

//#include "traps.h"
#include <math.h>
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
  double maxA, *ptr, absA;

  for (i = 0; i < N; i++) {
    maxA = 0.0;
    imax = i;

    for (k = i; k < N; k++)
      if ((absA = fabs(A[k][i])) > maxA) {
        maxA = absA;
        imax = k;
      }

    if (maxA < Tol) return 0; //failure, matrix is degenerate

    if (imax != i) {
      //pivoting P
      j = P[i];
      P[i] = P[imax];
      P[imax] = j;

      //pivoting rows of A
      ptr = A[i];
      A[i] = A[imax];
      A[imax] = ptr;

      //counting pivots starting from N (for determinant)
      P[N]++;
    }

    for (j = i + 1; j < N; j++) {
      A[j][i] /= A[i][i];

      for (k = i + 1; k < N; k++)
        A[j][k] -= A[j][i] * A[i][k];
    }
  }
  return 1;

}

