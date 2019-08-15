#ifndef CGRANode_H
#define CGRANode_H

#include "CGRALink.h"
#include <llvm/IR/Function.h>
#include <llvm/IR/Value.h>
#include <llvm/Support/raw_ostream.h>
#include <llvm/Support/FileSystem.h>
#include <list>
#include <string>

using namespace std;
using namespace llvm;

class CGRALink;

class CGRANode
{
  private:
    typedef std::pair<Value*, StringRef> DFG_Node;
    int ID;
    int RegisterCount;
    list<float> registers;
    int CtrlMemSize;
    int currentCtrlItems;
    float* CtrlMem;
    list<CGRALink*> in_links;
    list<CGRALink*> out_links;

    // functional unit occupied with cycle going on
    int CycleBoundary;
    bool* fu_occupied;
    DFG_Node* dfg_opt;
    map<CGRALink*,bool*> xbar_occupied;

  public:
    CGRANode(int, int, int);
    void setID(int);
    int getID();
    void attachInLink(CGRALink*);
    void attachOutLink(CGRALink*);
    list<CGRALink*> getInLinks();
    list<CGRALink*> getOutLinks();
    CGRALink* getInLink(CGRANode*);
    CGRALink* getOutLink(CGRANode*);
    list<CGRANode*> getOutNeighbors();

    void constructMRRG(int, int);
    bool canOccupyFU(int);
    bool canOccupyXbar(CGRALink*, int);
    void setOpt(DFG_Node, int, int);
    void configXbar(CGRALink*, int, int);
    void addRegisterValue(float);
    list<CGRALink*> getAvailableInLinks(int);
    list<CGRALink*> getAvailableOutLinks(int);
    list<CGRANode*> getAvailableOutNeighbors(int);
    int getAvailableRegisterCount();
    int getMinIdleCycle(int);
    int getCurrentCtrlMemItems();
};

#endif
