
#include "blowfish.h"
#include "bf_locl.h"

/* Blowfish as implemented from 'Blowfish: Springer-Verlag paper'
 * (From LECTURE NOTES IN COIMPUTER SCIENCE 809, FAST SOFTWARE ENCRYPTION,
 * CAMBRIDGE SECURITY WORKSHOP, CAMBRIDGE, U.K., DECEMBER 9-11, 1993)
 */

#if (BF_ROUNDS != 16) && (BF_ROUNDS != 20)
If you set BF_ROUNDS to some value other than 16 or 20, you will have
to modify the code.
#endif

void BF_encrypt(data,key,encrypt)
BF_LONG *data;
BF_KEY *key;
int encrypt;
  {
  register BF_LONG l,r,temp,*p,*s;

  p=key->P;
  s= &(key->S[0]);
  l=data[0];
  r=data[1];

  if (encrypt)
    {
    l^=p[0];
    int i=1;
    for (; i<21; ++i) {
      BF_ENC(r,l,s,p[i]);
      // we only consider BF_ENC function for now.
      temp = r;
      r = l;
      l = temp;
    }
    r^=p[0];
    }
  data[1]=l&0xffffffff;
  data[0]=r&0xffffffff;
  }
