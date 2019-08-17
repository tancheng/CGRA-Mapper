/*
 * ======================================================================
 * cgraPass.cpp
 * ======================================================================
 * CGRA pass implementation.
 *
 * Author : Cheng Tan
 *   Date : July 16, 2019
 */

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
    cgraPass() : FunctionPass(ID) {}
   
    bool runOnFunction(Function &m_F) override {
      DFG* dfg = new DFG(m_F);
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
      while (1) {
        int cycle = 0;
        mapper->constructMRRG(cgra, II);
        fail = false;
        for (list<DFG::Node>::iterator dfgNode=dfg->nodes.begin(); 
            dfgNode!=dfg->nodes.end(); ++dfgNode) {
          list<map<CGRANode*, int>> paths;
          for (int i=0; i<rows; ++i) {
            for (int j=0; j<columns; ++j) {
              CGRANode* fu = cgra->nodes[i][j];
//              errs()<<"DEBUG cgrapass: dfg node: "<<*(*dfgNode).first<<",["<<i<<"]["<<j<<"]\n";
              map<CGRANode*, int> tempPath = 
                mapper->calculateCost(cgra, dfg, II, *dfgNode, fu);
              if(tempPath.size() != 0)
                paths.push_back(tempPath);
              else
                errs()<<"DEBUG no available path?\n";
            }
          }
          // TODO: already found a possible mapping
          map<CGRANode*, int> optimalPath = mapper->getPathWithMinCost(paths);
          if (optimalPath.size() != 0) {
            if (!mapper->schedule(cgra, dfg, II, *dfgNode, optimalPath)) {
              errs()<<"DEBUG fail1 in schedule()\n";
              fail = true;
              break;
            }
//            errs()<<"DEBUG success in schedule()\n";
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
      errs() <<"\u2191 \u2193 \u21e7 \u21e9 \u2192 \u21c4"<<"\n";
      return false;
    }
  };
}

char cgraPass::ID = 0;
static RegisterPass<cgraPass> X("cgraPass", "DFG Pass Analyse", false, false);
