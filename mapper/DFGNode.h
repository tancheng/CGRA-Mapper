/*
 * ======================================================================
 * DFGNode.h
 * ======================================================================
 * DFG node implementation header file.
 *
 * Author : Cheng Tan
 *   Date : July 19, 2019
 */

#ifndef DFGNode_H
#define DFGNode_H

#include <llvm/IR/Value.h>
#include <llvm/IR/Instruction.h>
#include <llvm/IR/Instructions.h>
#include <llvm/Support/raw_ostream.h>

#include <string>
#include <list>
#include <stdio.h>

#include "DFGEdge.h"

using namespace llvm;
using namespace std;

class DFGEdge;

class DFGNode {
  private:
    int m_id;
    Instruction* m_inst;
    Value* m_value;
    StringRef m_stringRef;
    string m_opcodeName;
    list<DFGEdge*> m_inEdges;
    list<DFGEdge*> m_outEdges;
    list<DFGNode*>* m_succNodes;
    list<DFGNode*>* m_predNodes;
    bool m_isMapped;
    int m_numConst;
    string m_optType;
    string m_fuType;

  public:
    DFGNode(int, Instruction*, StringRef);
    int getID();
    void setID(int);
    bool isMapped();
    void setMapped();
    void clearMapped();
    bool isLoad();
    bool isStore();
    bool isBranch();
    bool isPhi();
    bool isCmp();
    bool isBitcast();
    bool isGetptr();
    Instruction* getInst();
    StringRef getStringRef();
    string getOpcodeName();
    list<DFGNode*>* getPredNodes();
    list<DFGNode*>* getSuccNodes();
    bool isSuccessorOf(DFGNode*);
    bool isPredecessorOf(DFGNode*);
    void setInEdge(DFGEdge*);
    void setOutEdge(DFGEdge*);
    void cutEdges();
    string getJSONOpt();
    string getFuType();
    void addConst();
    void removeConst();
    int getNumConst();
    void initType();
};

#endif
