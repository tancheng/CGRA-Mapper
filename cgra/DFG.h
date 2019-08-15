#include <llvm/IR/Function.h>
#include <llvm/IR/BasicBlock.h>
#include <llvm/IR/Value.h>
#include <llvm/IR/Instruction.h>
#include <llvm/IR/Instructions.h>
#include <llvm/Support/raw_ostream.h>
#include <llvm/Support/FileSystem.h>
#include <llvm/IR/Use.h>
#include <llvm/Analysis/CFG.h>
#include <list>

using namespace llvm;
using namespace std;

class DFG {
  private:
    int num;

    string changeIns2Str(Instruction* ins);
    //get value's name or inst's content
    StringRef getValueName(Value* v);

  public:
    DFG(Function&);
    typedef pair<Value*, StringRef> Node;
    typedef pair<Node, Node> Edge;
    list<Edge> inst_edges;
    //edges of data flow
    list<Edge> dfg_edges;
    //initial ordering of insts
    list<Node> nodes;

    void construct(Function &F);
    int getNodeCount();
    void DFS_on_DFG(Node, Node, list<Edge>*, list<Edge>*, list<list<Edge>>*);
    list<list<Edge>> getCycles();
    list<Node> getPredNodes(Node);
    int getID(Node);
};
