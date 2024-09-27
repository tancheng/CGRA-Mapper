/* testc - Test adpcm coder */

#include "adpcm.h"
#include <stdio.h>
#include "../bareBench.h"
#include "input.h"



#define NSAMPLES 1000
#define NINC  (NSAMPLES * 2)

char	abuf[NSAMPLES/2];

int main() {
    struct adpcm_state state = {};
    int n = 0;
    unsigned char * currentN = test_data;
    int maxN = sizeof(test_data);
    
    printf("Initial valprev=%d, index=%d\n", state.valprev, state.index);

    while(1) {
        int bytesIntoRead = ((unsigned int)currentN) - ((unsigned int)test_data);
        int testN = bytesIntoRead + NINC;
        n = (testN <= maxN) ? NINC : maxN - bytesIntoRead;

        if ( n == 0 ) break;
	
        adpcm_coder(currentN, abuf, n/2, &state);
        currentN = test_data + bytesIntoRead + n;
        //write(1, abuf, n/4);
    }
    
    printf("Final valprev=%d, index=%d\n", state.valprev, state.index);
    return 0;
}
