#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <math.h>
#include "polybench.h"
#include "conv.h"

/* Array initialization. */
static
void init_array(int ni, int nj, int nk,
		DATA_TYPE *alpha,
		DATA_TYPE *beta,
		DATA_TYPE POLYBENCH_2D(C,NI,NJ,ni,nj),
		DATA_TYPE POLYBENCH_2D(A,NI,NJ,ni,nj),
		DATA_TYPE POLYBENCH_2D(B,NK,NJ,nk,nj))
{
  int i, j;

  *alpha = 2;
  *beta = 3;
  for (i = 0; i < ni; i++)
    for (j = 0; j < nj; j++)
      C[i][j] = (DATA_TYPE) (i*j % ni) / ni;
  for (i = 0; i < ni; i++)
    for (j = 0; j < nj; j++)
      A[i][j] = (DATA_TYPE) (i*(j+1) % nk) / nk;
  for (i = 0; i < ni; i++)
    for (j = 0; j < nj; j++)
      B[i][j] = (DATA_TYPE) (i*(j+2) % nj) / nj;
}


/* DCE code. Must scan the entire live-out data.
   Can be used also to check the correctness of the output. */
static
void print_array(int ni, int nj,
		 DATA_TYPE POLYBENCH_2D(C,NI,NJ,ni,nj))
{
  int i, j;

  POLYBENCH_DUMP_START;
  POLYBENCH_DUMP_BEGIN("C");
  for (i = 0; i < ni; i++)
    for (j = 0; j < nj; j++) {
	if ((i * ni + j) % 20 == 0) fprintf (POLYBENCH_DUMP_TARGET, "\n");
	fprintf (POLYBENCH_DUMP_TARGET, DATA_PRINTF_MODIFIER, C[i][j]);
    }
  POLYBENCH_DUMP_END("C");
  POLYBENCH_DUMP_FINISH;
}


/* Main computational kernel. The whole function will be timed,
   including the call and return. */
int kernel(int ni, int nj, int nk,
	   DATA_TYPE alpha,
	   DATA_TYPE beta,
	   DATA_TYPE POLYBENCH_2D(C,NI,NJ,ni,nj),
	   DATA_TYPE POLYBENCH_2D(A,NI,NJ,ni,nj),
	   DATA_TYPE POLYBENCH_2D(B,NI,NJ,ni,nj))
{
  int x = 0, i = 0, j = 0, k = 0;

//BLAS PARAMS
//TRANSA = 'N'
//TRANSB = 'N'
//A is NIxNK
//B is NKxNJ
//C is NIxNJ

  int total = NI * NJ;
  int out = 0;
  // #pragma clang loop unroll_count(4) vectorize(disable)
  //#pragma clang loop unroll_count(1) vectorize_width(4)
  //#pragma clang loop vectorize_width(4)
  for (x = 0; x < total; x+=4) {
    int y = x+1;
    i = y / NJ;
    j = y % NJ;
    out += A[i][j] * B[i][j];
    i = x / NJ;
    j = x % NJ;
    out += A[i][j] * B[i][j];
    i = x / NJ;
    j = x % NJ;
    out += A[i][j] * B[i][j];
    i = x / NJ;
    j = x % NJ;
    out += A[i][j] * B[i][j];
  }

  /*
  for (i = 0; i < NI; i++) {
    // #pragma clang loop unroll_count(2) vectorize(disable)
    #pragma clang loop unroll_count(1) vectorize_width(4)
    for (j = 0; j < NJ; j++) {
      out += A[i][j] * B[i][j];
    }
  }
  */
  return out;
}


int main(int argc, char** argv)
{
  /* Retrieve problem size. */
  int ni = NI;
  int nj = NJ;
  int nk = NK;

  /* Variable declaration/allocation. */
  DATA_TYPE alpha;
  DATA_TYPE beta;
  POLYBENCH_2D_ARRAY_DECL(C,DATA_TYPE,NI,NJ,ni,nj);
  POLYBENCH_2D_ARRAY_DECL(A,DATA_TYPE,NI,NJ,ni,nj);
  POLYBENCH_2D_ARRAY_DECL(B,DATA_TYPE,NI,NJ,ni,nj);

  /* Initialize array(s). */
  init_array (ni, nj, nk, &alpha, &beta,
	      POLYBENCH_ARRAY(C),
	      POLYBENCH_ARRAY(A),
	      POLYBENCH_ARRAY(B));

  /* Start timer. */
  polybench_start_instruments;

  /* Run kernel. */
  int out = kernel(ni, nj, nk,
	           alpha, beta,
	           POLYBENCH_ARRAY(C),
	           POLYBENCH_ARRAY(A),
	           POLYBENCH_ARRAY(B));

  /* Stop and print timer. */
  polybench_stop_instruments;
  polybench_print_instruments;

  /* Prevent dead-code elimination. All live-out data must be printed
     by the function call in argument. */
  polybench_prevent_dce(print_array(ni, nj,  POLYBENCH_ARRAY(C)));

  /* Be clean. */
  POLYBENCH_FREE_ARRAY(C);
  POLYBENCH_FREE_ARRAY(A);
  POLYBENCH_FREE_ARRAY(B);

  return 0;
}
