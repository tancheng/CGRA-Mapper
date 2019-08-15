#include <llvm/IR/Function.h>
#include <llvm/IR/Value.h>
#include "DFG.h"
#include "CGRA.h"

#define MAX_COST 100
#define DELAY_COST 1

using namespace llvm;

class Mapper {
  private:
    typedef std::pair<Value*, StringRef> DFG_Node;
    int maxMappingCycle;
    map<DFG_Node, CGRANode*> mapping;
    map<DFG_Node, int> mapping_timing;
//    CGRANode* getMappedCGRANode(DFG_Node);
//    int getMappedCGRANodeTiming(DFG_Node);

  public:
    Mapper(){}
    int getResMII(DFG*, CGRA*);
    int getRecMII(DFG*);
    void constructMRRG(CGRA*, int);
    map<CGRANode*, int> dijkstra_search(CGRA*, DFG*, DFG_Node, CGRANode*);
    map<CGRANode*, int> calculateCost(CGRA*, DFG*, DFG_Node, CGRANode*);
    bool schedule(CGRA*, DFG*, int, DFG_Node, map<CGRANode*, int>);
    int getMaxMappingCycle();
    void showSchedule(CGRA*, DFG*, int);
    map<CGRANode*, int> getPathWithMinCost(list<map<CGRANode*, int>>);
    bool tryToRoute(CGRA*, int, DFG_Node, CGRANode*, CGRANode*);
};
