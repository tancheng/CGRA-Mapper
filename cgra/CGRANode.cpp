/*
 * ======================================================================
 * CGRANode.cpp
 * ======================================================================
 * CGRA tile implementation.
 *
 * Author : Cheng Tan
 *   Date : July 16, 2019
 */

#include "CGRANode.h"
#include <stdio.h>

CGRANode::CGRANode(int t_ID, int t_RegisterCount, int t_CtrlMemSize) {
  ID = t_ID;
  RegisterCount = t_RegisterCount;
  CtrlMemSize = t_CtrlMemSize;
  CtrlMem = new float[t_CtrlMemSize];
  currentCtrlItems = 0;
}

void CGRANode::setID(int ID) {
  this->ID = ID;
}

int CGRANode::getID() {
  return ID;
}

void CGRANode::attachInLink(CGRALink *l) {
  in_links.push_back(l);
}

void CGRANode::attachOutLink(CGRALink *l) {
  out_links.push_back(l);
}

list<CGRALink*> CGRANode::getInLinks() {
  return in_links;
}

list<CGRALink*> CGRANode::getOutLinks() {
  return out_links;
}

list<CGRANode*> CGRANode::getOutNeighbors() {
  list<CGRANode*> neighbors;
  for (list<CGRALink*>::iterator link=out_links.begin();
      link!=out_links.end(); ++link)
    neighbors.push_back((*link)->getConnectedNode(this));
  return neighbors;
}

void CGRANode::constructMRRG(int t_CGRANodeCount, int t_II) {
  CycleBoundary = t_CGRANodeCount*t_II*t_II;
  fu_occupied = new bool[CycleBoundary];
  dfg_opt = new DFG_Node[CycleBoundary];
  for (int i=0; i<CycleBoundary; ++i)
    fu_occupied[i] = false;
}

bool CGRANode::canOccupyFU(int t_cycle, int t_II) {
  for (int c=t_cycle; c<CycleBoundary; c+=t_II) {
    if (fu_occupied[c]) {
      return false;
    }
  }
  return true;
}

void CGRANode::setOpt(DFG_Node t_opt, int t_cycle, int t_II) {
  for (int c=t_cycle; c<CycleBoundary; c+=t_II) {
    assert(!fu_occupied[c]);
    dfg_opt[c].first = t_opt.first;
    dfg_opt[c].second = t_opt.second;
    fu_occupied[c] = true;
    ++currentCtrlItems;
  }
}

// TODO: The configuration of xbar is also stored insde the config mem.
// So we should check whether there is space left in the config mem to hold it.
bool CGRANode::canOccupyXbar(CGRALink* outLink, int t_cycle) {
//  for(int c=cycle; c<CycleBoundary; c+=II)
//  {
//    dfg_opt[c].first = opt.first;
//    dfg_opt[c].second = opt.second;
//    fu_occupied[c] = true;
//  }

  return true;
}

void CGRANode::configXbar(CGRALink*, int, int)
{

}

void CGRANode::addRegisterValue(float t_value) {
  registers.push_back(t_value);
}

list<CGRALink*> CGRANode::getAvailableInLinks(int t_cycle) {
  list<CGRALink*> available_in_links;
  for (list<CGRALink*>::iterator link=in_links.begin();
      link!=in_links.end(); ++link) {
    if (!(*link)->isOccupied(t_cycle)) {
      available_in_links.push_back(*link);
    }
  }
  return available_in_links;
}

list<CGRALink*> CGRANode::getAvailableOutLinks(int t_cycle) {
  list<CGRALink*> available_out_links;
  for (list<CGRALink*>::iterator link=out_links.begin();
      link!=out_links.end(); ++link) {
    if (!(*link)->isOccupied(t_cycle)) {
      available_out_links.push_back(*link);
    }
  }
  return available_out_links;
}

int CGRANode::getAvailableRegisterCount() {
  return (RegisterCount - registers.size());
}

CGRALink* CGRANode::getInLink(CGRANode* t_node) {
  for (list<CGRALink*>::iterator link=in_links.begin();
      link!=in_links.end(); ++link) {
    if ((*link)->getSrc() == t_node) {
      return *link;
    }
  }
  // will definitely return one inlink
  assert(0);
}

CGRALink* CGRANode::getOutLink(CGRANode* t_node) {
  for (list<CGRALink*>::iterator link=out_links.begin();
      link!=out_links.end(); ++link) {
    if ((*link)->getDst() == t_node)
      return *link;
  }
  // will definitely return one outlink
  assert(0);
}

int CGRANode::getMinIdleCycle(int t_cycle, int t_II) {
  int tempCycle = t_cycle;
  while (tempCycle < CycleBoundary) {
    if (canOccupyFU(tempCycle, t_II))
      return tempCycle;
    ++tempCycle;
  }
  return CycleBoundary;
}

int CGRANode::getCurrentCtrlMemItems() {
  return currentCtrlItems;
}

