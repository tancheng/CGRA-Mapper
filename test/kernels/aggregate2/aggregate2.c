/* 32-tap FIR filter processing 1 point */
/* Modified to use arrays - SMP */

//#include "traps.h"

#define SIZE 10000

int nnz = 100;
float val[SIZE];
int col[SIZE];
int row[SIZE];
float** feature;
float** output;

void kernel(int, int, float val[], int col[], int row[], float** feature, float** output);

int main()
{

//  input_dsp (input, NTAPS, 0);

  kernel(nnz, 50, val, col, row, feature, output);

//  output_dsp (input, NTAPS, 0);
//  output_dsp (coefficients, NTAPS, 0);
//  output_dsp (output, NTAPS, 0);
  return 0;
}

void kernel(int nnz, int size, float val[], int col[], int row[], float** feature, float** output)
{
  int i = 0;
  int j = 0;
  float temp;

  /*
  for (i = 0; i < nnz; ++i) {
    for (j = 0; j < size; ++j) {
      temp = val[i] * feature[ col[i] ][ j ];
      output[ row[i] ][ j ] += temp;
    }
  }
  */
  int X = nnz * size;
  int x = 0;
  for (x = 0; x < X; ++x) {
    i = x / size;
    j = x % size;
    temp = val[i] * feature[ col[i] ][ j ];
    output[ row[i] ][ j ] += temp;
  }

}

