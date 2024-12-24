/*
 * ======================================================================
 * CGRANode.h
 * ======================================================================
 * CGRA tile implementation header file.
 *
 * Author : Cheng Tan
 *   Date : July 16, 2019
 */

#ifndef CGRANode_H
#define CGRANode_H

#include "CGRALink.h"
#include "DFGNode.h"
#include <iostream>
//#include <llvm/IR/Function.h>
//#include <llvm/IR/Value.h>
//#include <llvm/Support/raw_ostream.h>
//#include <llvm/Support/FileSystem.h>
#include <list>
#include <string>

using namespace std;
using namespace llvm;

class CGRALink;
class DFGNode;

class CGRANode {

  private:
//    typedef std::pair<Value*, StringRef> DFG_Node;
    int m_id;
    int m_x;
    int m_y;
    int m_registerCount;
    list<float> m_registers;
    int m_ctrlMemSize;
    int m_currentCtrlMemItems;
    float* m_ctrlMem;
    list<CGRALink*> m_inLinks;
    list<CGRALink*> m_outLinks;
    list<CGRALink*>* m_occupiableInLinks;
    list<CGRALink*>* m_occupiableOutLinks;
    list<CGRANode*>* m_neighbors;

    // functional unit occupied with cycle going on
    int m_cycleBoundary;
    int* m_fuOccupied;
    DFGNode** m_dfgNodes;
    map<CGRALink*,bool*> m_xbarOccupied;
    bool m_disabled;
    bool m_canReturn;
    bool m_canStore;
    bool m_canLoad;
    bool m_canCall;
    bool m_canAdd;
    bool m_canMul;
    bool m_canShift;
    bool m_canPhi;
    bool m_canSel;
    bool m_canCmp;
    bool m_canMAC;
    bool m_canLogic;
    bool m_canBr;
    bool m_supportComplex;
    bool m_supportPathDim;
    bool m_supportVectorization;
    int** m_regs_duration;
    int** m_regs_timing;
    vector<list<pair<DFGNode*, int>>*> m_dfgNodesWithOccupyStatus;

  public:
    CGRANode(int, int, int);
//    CGRANode(int, int, int, int, int);
    void setRegConstraint(int);
    void setCtrlMemConstraint(int);
    void setID(int);
    void setLocation(int, int);
    int getID();
    bool enableFunctionality(string);
    void enableReturn();
    void enableStore();
    void enableLoad();
    void enableCall();
    void enableComplex();
    void enablePathDim();
    void enableVectorization();
    void enableAdd();
    void enableMul();
    void enableShift();
    void enablePhi();
    void enableSel();
    void enableCmp();
    void enableMAC();
    void enableLogic();
    void enableBr();

    void attachInLink(CGRALink*);
    void attachOutLink(CGRALink*);
    list<CGRALink*>* getInLinks();
    list<CGRALink*>* getOutLinks();
    CGRALink* getInLink(CGRANode*);
    CGRALink* getOutLink(CGRANode*);
    list<CGRANode*>* getNeighbors();

    void constructMRRG(int, int);
    bool canSupport(DFGNode*);
    bool isOccupied(int, int);
    // bool canOccupy(int, int);
    bool canOccupy(DFGNode*, int, int);
    void setDFGNode(DFGNode*, int, int, bool);
    void configXbar(CGRALink*, int, int);
    void addRegisterValue(float);
    list<CGRALink*>* getOccupiableInLinks(int, int);
    list<CGRALink*>* getOccupiableOutLinks(int, int);
    int getAvailableRegisterCount();
    int getMinIdleCycle(DFGNode*, int, int);
    int getCurrentCtrlMemItems();
    int getX();
    int getY();
    bool canReturn();
    bool canStore();
    bool canLoad();
    bool canCall();
    bool supportComplex();
    bool supportPathDim();
    bool supportVectorization();
    bool canAdd();
    bool canMul();
    bool canShift();
    bool canPhi();
    bool canSel();
    bool canCmp();
    bool canMAC();
    bool canLogic();
    bool canBr();
    DFGNode* getMappedDFGNode(int);
    bool containMappedDFGNode(DFGNode*, int);
    void allocateReg(CGRALink*, int, int, int);
    void allocateReg(int, int, int, int);
    int* getRegsAllocation(int);
    void disable();
    bool isDisabled();
    void disableAllFUs();
};

#endif
