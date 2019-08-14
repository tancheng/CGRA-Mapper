#include "CGRALink.h"
#include <assert.h>

CGRALink::CGRALink(int link_id)
{
  setID(link_id);
}

void CGRALink::connect(CGRANode* source, CGRANode* dest)
{
  src = source;
  dst = dest;
}

void CGRALink::connectSrc(CGRANode* node)
{
  assert(src == NULL);
  src = node;
}

void CGRALink::connectDst(CGRANode* node)
{
  assert(dst == NULL);
  dst = node;
}

CGRANode* CGRALink::getConnectedNode(CGRANode* node)
{
  if( node != src and node != dst)
    return NULL;
  if(src == node)
    return dst;
  else
    return src;
}

int CGRALink::getID()
{
  return ID;
}

void CGRALink::setID(int ID)
{
  this->ID = ID;
}

void CGRALink::constructMRRG(int CGRANodeCount, int II)
{
  CycleBoundary = CGRANodeCount*II*II;
  occupied = new bool[CycleBoundary];
  for(int i=0; i<CycleBoundary; ++i)
    occupied[i] = false;
}

bool CGRALink::isOccupied(int cycle)
{
  return occupied[cycle];
}

void CGRALink::occupy(int cycle, int II)
{
  for(int c=cycle; c<CycleBoundary; c+=II)
    occupied[c] = true;
}

CGRANode* CGRALink::getSrc()
{
  return src;
}
CGRANode* CGRALink::getDst()
{
  return dst;
}

