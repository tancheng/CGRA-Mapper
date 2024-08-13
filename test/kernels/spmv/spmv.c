#define SIZE 10000

int nnz = 100;
int val[SIZE];
int col[SIZE];
int row[SIZE];
int feature[SIZE];
int output[SIZE];

void kernel(int nnz, int val[], int col[], int row[], int feature[], int output[]);

int main()
{

//  input_dsp (input, NTAPS, 0);

  kernel(nnz, val, col, row, feature, output);

//  output_dsp (input, NTAPS, 0);
//  output_dsp (coefficients, NTAPS, 0);
//  output_dsp (output, NTAPS, 0);
  return 0;
}

void kernel(int nnz, int val[], int col[], int row[], int feature[], int output[])
{
  int i = 0;
  int temp;

  //#pragma clang loop unroll_count(4)
  for (i = 0; i < nnz; ++i) {
    temp = val[i] * feature[ col[i] ];
    output[ row[i] ] += temp;
  }
}

