#include <llvm/IR/Function.h>
#include <llvm/Pass.h>
#include <stdio.h>
#include "Mapper.h"

using namespace llvm;
namespace {
  struct cgraPass : public FunctionPass {
  public:
    static char ID;
    Mapper* mapper;
//    int func_times = 0;
    cgraPass() : FunctionPass(ID) {}
   
    bool runOnFunction(Function &F) override {
//      if(func_times==1)
//        return false;
//      func_times++;
      DFG* dfg = new DFG(F);
      int rows = 4;
      int columns = 4;
      CGRA* cgra = new CGRA(rows, columns);
      mapper = new Mapper();
      int ResMII = mapper->getResMII(dfg, cgra);
      errs() << "==================================\n";
      errs() << "[ResMII: " << ResMII << "]\n";
      int RecMII = mapper->getRecMII(dfg);
      errs() << "==================================\n";
      errs() << "[RecMII: " << RecMII << "]\n";
      int II = ResMII;
      if(II < RecMII)
        II = RecMII;
      
      bool fail = false;
      while(1)
      {
        int cycle = 0;
        int optimal_cost = MAX_COST;
        CGRANode* optimal_fu = NULL;
        mapper->constructMRRG(cgra, II);
        fail = false;
        for(list<DFG::Node>::iterator dfg_node=dfg->nodes.begin(); dfg_node!=dfg->nodes.end(); ++dfg_node)
        {
          list<map<CGRANode*, int>> paths;
          for(int i=0; i<rows; ++i)
          {
            for(int j=0; j<columns; ++j)
            {
              CGRANode* fu = cgra->nodes[i][j];
//              errs()<<"DEBUG cgrapass: dfg node: "<<*(*dfg_node).first<<",["<<i<<"]["<<j<<"]\n";
              map<CGRANode*, int> temp_path = mapper->calculateCost(cgra, dfg, *dfg_node, fu);
              if(temp_path.size() != 0)
                paths.push_back(temp_path);
              else
                errs()<<"DEBUG no available path?\n";
            }
          }
          // TODO: already found a possible mapping
          map<CGRANode*, int> optimal_path = mapper->getPathWithMinCost(paths);
          if(optimal_path.size() != 0)
          {
            if(!mapper->schedule(cgra, dfg, II, *dfg_node, optimal_path))
            {
              errs()<<"DEBUG fail1 in schedule()\n";
              fail = true;
              break;
            }
            errs()<<"DEBUG success in schedule()\n";
          } else {
            errs()<<"DEBUG fail2 in schedule()\n";
            fail = true;
            break;
          }
        }
        if(!fail)
          break;
        ++II;
      }
      mapper->showSchedule(cgra, dfg, II);
      errs() << "==================================\n";
      errs() << "[done]\n";
      errs() << "==================================\n";
      return false;
    }
  };
}

char cgraPass::ID = 0;
static RegisterPass<cgraPass> X("cgraPass", "DFG Pass Analyse", false, false);
