/*
 * ======================================================================
 * DFGEdge.h
 * ======================================================================
 * DFG edge implementation header file.
 *
 * Author : Cheng Tan
 *   Date : July 19, 2019
 */

#ifndef DFGEdge_H
#define DFGEdge_H

#include <llvm/Support/raw_ostream.h>
#include <llvm/Support/FileSystem.h>

#include "DFGNode.h"

using namespace llvm;

class DFGNode;

class DFGEdge
{
  private:
    int m_id;
    DFGNode *m_src;
    DFGNode *m_dst;
    bool m_isCtrlEdge;

    // "m_isInterEdge" is used to specify whether this DFGEdge trnasfers inter-basicblock or inter-iteration data.
    bool m_isInterEdge;

  public:
    DFGEdge(int, DFGNode*, DFGNode*);
    DFGEdge(int, DFGNode*, DFGNode*, bool);
    void setID(int);
    int getID();
    DFGNode* getSrc();
    DFGNode* getDst();
    void connect(DFGNode*, DFGNode*);
    DFGNode* getConnectedNode(DFGNode*);
    bool isCtrlEdge();

    // Sets m_isInterEdge = true/false.
    void setInterEdge(bool);

    // Reads m_isInterEdge.
    bool isInterEdge();
};

#endif
