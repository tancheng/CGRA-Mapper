/* 32-tap FIR filter processing 1 point */
/* Modified to use arrays - SMP */

//#include "traps.h"

#include<iostream>

using namespace std;

#define SIZE 10000

void kernel(int, int**, int*, int*, int*);

int main()
{

  int maxNodeCount = 100;
  int maxEdgeCount = 300;

  int* col = new int[maxEdgeCount];
  int* row = new int[maxEdgeCount];
  int* value = new int[maxEdgeCount];
  int** matrix = new int*[maxNodeCount];
  for(int i=0; i<maxNodeCount; ++i) {
    matrix[i] = new int[maxNodeCount];
  }

  matrix[0][1] = 3;
  matrix[3][4] = 7;

  kernel(maxNodeCount, matrix, row, col, value);

  cout<<"row: ";
  for(int i=0; i<maxEdgeCount; ++i) {
    cout<<row[i]<<" ";
  }
  cout<<endl;
  cout<<"col: ";
  for(int i=0; i<maxEdgeCount; ++i) {
    cout<<col[i]<<" ";
  }
  cout<<endl;
  cout<<"value: ";
  for(int i=0; i<maxEdgeCount; ++i) {
    cout<<value[i]<<" ";
  }
  cout<<endl;

  return 0;
}

void kernel(int maxNodeCount, int** matrix, int* row, int* col, int* value) {
  /*
  for (i = 0; i < nnz; ++i) {
    for (j = 0; j < size; ++j) {
      temp = val[i] * feature[ col[i] ][ j ];
      output[ row[i] ][ j ] += temp;
    }
  }
  */
  int index=0;
  int total = maxNodeCount * maxNodeCount;
  for(int x=0; x<total; ++x) {
    int i = x / maxNodeCount;
    int j = x % maxNodeCount;
    value[index] = matrix[i][j];
    row[index] = i;
    col[index] = j;
    if(matrix[i][j] != 0) {
      index++;
    }
  }

}

