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
#include <llvm/IR/BasicBlock.h>

#include <string>
#include <list>
#include <stdio.h>
#include <iostream>

#include "DFGEdge.h"

using namespace llvm;
using namespace std;

class DFGEdge;

class DFGNode {
  private:
    // Original id that is ordered in the original execution order (i.e.,
    // CPU/IR execution sequential ordering).
    int m_id;
    bool m_precisionAware;
    Instruction* m_inst;
    Value* m_value;
    StringRef m_stringRef;
    string m_opcodeName;
    // m_pathName is the derived from basic block of llvm
    string m_pathName;  
    list<DFGEdge*> m_inEdges;
    list<DFGEdge*> m_outEdges;
    list<DFGNode*>* m_succNodes;
    list<DFGNode*>* m_predNodes;
    list<DFGNode*>* m_patternNodes;
    list<int>* m_cycleID;
    bool m_isMapped;
    int m_numConst;
    string m_optType;
    string m_fuType;
    bool m_combined;
    bool m_merged;
    bool m_isPatternRoot;
    bool m_critical;
    int m_level;
    int m_execLatency;
    bool m_pipelinable;
    // "m_predicated" indicates whether the execution of the node depends on
    // predication or not (i.e., the predecessor probably is a "branch"). 
    bool m_isPredicatee;
    list<DFGNode*>* m_predicatees;
    bool m_isPredicater;
    DFGNode* m_patternRoot;
    void setPatternRoot(DFGNode*);

  public:
    DFGNode(int, bool, Instruction*, StringRef, string);
    int getID();
    void setID(int);
    void setLevel(int);
    int getLevel();
    bool isMapped();
    void setMapped();
    void clearMapped();
    bool isLoad();
    bool isStore();
    bool isReturn();
    bool isCall();
    bool isBranch();
    bool isPhi();
    bool isAdd();
    bool isMul();
    bool isCmp();
    bool isBitcast();
    bool isGetptr();
    bool isSel();
    bool isMAC();
    bool isLogic();
    bool isOpt(string);
    bool isVectorized();
    bool hasCombined();
    void setCombine();
    bool hasMerged();
    void setMerge();
    void addPatternPartner(DFGNode*);
    Instruction* getInst();
    StringRef getStringRef();
    string getOpcodeName();
    string getPathName();
    list<DFGNode*>* getPredNodes();
    list<DFGNode*>* getSuccNodes();
    bool isSuccessorOf(DFGNode*);
    bool isPredecessorOf(DFGNode*);
    bool isOneOfThem(list<DFGNode*>*);
    void setInEdge(DFGEdge*);
    void setOutEdge(DFGEdge*);
    void cutEdges();
    string getJSONOpt();
    string getFuType();
    void addConst();
    void removeConst();
    int getNumConst();
    void initType();
    bool isPatternRoot();
    DFGNode* getPatternRoot();
    list<DFGNode*>* getPatternNodes();
    void setCritical();
    void addCycleID(int);
    bool isCritical();
    int getCycleID();
    list<int>* getCycleIDs();
    void addPredicatee(DFGNode*);
    list<DFGNode*>* getPredicatees();
    void setPredicatee();
    bool isPredicatee();
    bool isPredicater();
    bool shareSameCycle(DFGNode*);
    void setExecLatency(int);
    bool isMultiCycleExec();
    int getExecLatency();
    void setPipelinable();
    bool isPipelinable();
    bool shareFU(DFGNode*);
};

#endif
