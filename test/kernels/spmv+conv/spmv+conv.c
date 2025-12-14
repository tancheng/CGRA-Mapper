#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <math.h>
#include "polybench.h"
#include "conv.h"
#define SIZE 10000

int nnz = 400000;
int val[SIZE];
int col[SIZE];
int row[SIZE];
int feature[SIZE];
int output[SIZE];

int kernel(int nnz, int val[], int col[], int row[], int feature[], int output[],
    DATA_TYPE POLYBENCH_2D(C,NI,NJ,ni,nj),
	   DATA_TYPE POLYBENCH_2D(A,NI,NJ,ni,nj),
	   DATA_TYPE POLYBENCH_2D(B,NI,NJ,ni,nj));

int main()
{

  // conv
  POLYBENCH_2D_ARRAY_DECL(C,DATA_TYPE,NI,NJ,ni,nj);
  POLYBENCH_2D_ARRAY_DECL(A,DATA_TYPE,NI,NJ,ni,nj);
  POLYBENCH_2D_ARRAY_DECL(B,DATA_TYPE,NI,NJ,ni,nj);

  kernel(nnz, val, col, row, feature, output,	           POLYBENCH_ARRAY(C),
	           POLYBENCH_ARRAY(A),
	           POLYBENCH_ARRAY(B));

//  output_dsp (input, NTAPS, 0);
//  output_dsp (coefficients, NTAPS, 0);
//  output_dsp (output, NTAPS, 0);
  return 0;
}

int kernel(int nnz, int val[], int col[], int row[], int feature[], int output[],
    DATA_TYPE POLYBENCH_2D(C,NI,NJ,ni,nj),
	   DATA_TYPE POLYBENCH_2D(A,NI,NJ,ni,nj),
	   DATA_TYPE POLYBENCH_2D(B,NI,NJ,ni,nj))
{
  int i = 0;
  int temp;

  // conv
  int x,y;
  int out = 0;

  //#pragma clang loop unroll_count(4)
  for (i = 0; i < nnz; ++i) {
    // spmv
    temp = val[i] * feature[ col[i] ];
    output[ row[i] ] += temp;
    // conv
    x = i / NI;
    y = i % NJ;
    out += A  [x][y] * B[x][y];
  }
  return out;
}