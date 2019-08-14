#ifndef CGRALink_H
#define CGRALink_H

#include <llvm/Support/raw_ostream.h>
#include <llvm/Support/FileSystem.h>

#include "CGRANode.h"

using namespace llvm;

class CGRANode;

class CGRALink
{
  private:
    int ID;
    CGRANode *src;
    CGRANode *dst;

    int CycleBoundary;
    bool* occupied;

  public:
    CGRALink(){}
    CGRALink(int);
    void setID(int);
    int getID();
    CGRANode*  getSrc();
    CGRANode*  getDst();
    void connect(CGRANode*, CGRANode*);
    void connectSrc(CGRANode*);
    void connectDst(CGRANode*);
    CGRANode* getConnectedNode(CGRANode*); 

    void constructMRRG(int, int);
    bool isOccupied(int);
    void occupy(int, int);
};

#endif
