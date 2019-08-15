#include "CGRANode.h"
#include <stdio.h>

CGRANode::CGRANode(int ID, int RegisterCount, int CtrlMemSize)
{
  this->ID = ID;
  this->RegisterCount = RegisterCount;
  this->CtrlMemSize = CtrlMemSize;
  CtrlMem = new float[CtrlMemSize];
  currentCtrlItems = 0;
}

void CGRANode::setID(int ID)
{
  this->ID = ID;
}

int CGRANode::getID()
{
  return ID;
}

void CGRANode::attachInLink(CGRALink *l)
{
  in_links.push_back(l);
}

void CGRANode::attachOutLink(CGRALink *l)
{
  out_links.push_back(l);
}

list<CGRALink*> CGRANode::getInLinks()
{
  return in_links;
}

list<CGRALink*> CGRANode::getOutLinks()
{
  return out_links;
}

list<CGRANode*> CGRANode::getOutNeighbors()
{
  list<CGRANode*> neighbors;
  for(list<CGRALink*>::iterator link=out_links.begin(); link!=out_links.end(); ++link)
  {
    neighbors.push_back((*link)->getConnectedNode(this));
  }
  return neighbors;
}

void CGRANode::constructMRRG(int CGRANodeCount, int II)
{
  CycleBoundary = CGRANodeCount*II*II;
  fu_occupied = new bool[CycleBoundary];
  dfg_opt = new DFG_Node[CycleBoundary];
  for(int i=0; i<CycleBoundary; ++i)
  {
    fu_occupied[i] = false;
//    dfg_opt[i].first = NULL;
//    dfg_opt[i].second = NULL;
  }
}

bool CGRANode::canOccupyFU(int cycle) {
  return !fu_occupied[cycle];
}

void CGRANode::setOpt(DFG_Node opt, int cycle, int II) {
  for (int c=cycle; c<CycleBoundary; c+=II) {
    assert(!fu_occupied[c]);
    dfg_opt[c].first = opt.first;
    dfg_opt[c].second = opt.second;
    fu_occupied[c] = true;
    ++currentCtrlItems;
  }
}

// TODO: The configuration of xbar is also stored insde the config mem.
// So we should check whether there is space left in the config mem to hold it.
bool CGRANode::canOccupyXbar(CGRALink* outLink, int t_cycle)  {
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

void CGRANode::addRegisterValue(float value)
{
  registers.push_back(value);
}

list<CGRALink*> CGRANode::getAvailableInLinks(int cycle)
{
  list<CGRALink*> available_in_links;
  for(list<CGRALink*>::iterator link=in_links.begin(); link!=in_links.end(); ++link)
  {
    if(!(*link)->isOccupied(cycle))
    {
      available_in_links.push_back(*link);
    }
  }
  return available_in_links;
}

list<CGRALink*> CGRANode::getAvailableOutLinks(int cycle)
{
  list<CGRALink*> available_out_links;
  for(list<CGRALink*>::iterator link=out_links.begin(); link!=out_links.end(); ++link)
  {
    if(!(*link)->isOccupied(cycle))
    {
      available_out_links.push_back(*link);
    }
  }
  return available_out_links;
}

list<CGRANode*> CGRANode::getAvailableOutNeighbors(int cycle)
{
  list<CGRANode*> available_out_neighbors;
  for(list<CGRALink*>::iterator link=out_links.begin(); link!=out_links.end(); ++link)
  {
    CGRANode* neighbor = (*link)->getConnectedNode(this);
    if(neighbor->canOccupyFU(cycle))
      available_out_neighbors.push_back(neighbor);
  }
  return available_out_neighbors;
}

int CGRANode::getAvailableRegisterCount()
{
  return (RegisterCount - registers.size());
}

CGRALink* CGRANode::getInLink(CGRANode* node)
{
  for(list<CGRALink*>::iterator link=in_links.begin(); link!=in_links.end(); ++link)
  {
    if((*link)->getSrc() == node)
    {
      return *link;
    }
  }
  // will definitely return one inlink
  assert(0);
}

CGRALink* CGRANode::getOutLink(CGRANode* node) {
  for (list<CGRALink*>::iterator link=out_links.begin(); link!=out_links.end(); ++link) {
    if ((*link)->getDst() == node)
      return *link;
  }
  // will definitely return one outlink
  assert(0);
}

int CGRANode::getMinIdleCycle(int t_cycle) {
  int tempCycle = t_cycle;
  while (tempCycle < CycleBoundary) {
    if (canOccupyFU(tempCycle))
      return tempCycle;
    ++tempCycle;
  }
  return CycleBoundary;
}

int CGRANode::getCurrentCtrlMemItems() {
  return currentCtrlItems;
}

