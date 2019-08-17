/*
 * ======================================================================
 * CGRA.cpp
 * ======================================================================
 * CGRA implementation.
 * 
 * Author : Cheng Tan
 *   Date : July 16, 2019
 */

#include "CGRA.h"

CGRA::CGRA(int rows, int columns)
{
  this->rows = rows;
  this->columns = columns;
  FUCount = rows * columns;
  nodes = new CGRANode**[rows];
  // unidirection connections
  LinkCount = 2 * (rows * (columns-1) + (rows-1) * columns);
  links = new CGRALink*[LinkCount];
 
  // initialize CGRA nodes
  int node_id = 0;
  for(int i=0; i<rows; ++i)
  {
    nodes[i] = new CGRANode*[columns];
    for(int j=0; j<columns; ++j)
    {
      nodes[i][j] = new CGRANode(node_id++, REG_COUNT, CTRL_MEM_SIZE);
    }
  }

  // connect CGRA nodes with links
  int link_id = 0;
  for(int i=0; i<rows; ++i)
  {
    for(int j=0; j<columns; ++j)
    {
      if(i<rows-1)
      {
        links[link_id] = new CGRALink(link_id);
        nodes[i][j]->attachOutLink(links[link_id]);
        nodes[i+1][j]->attachInLink(links[link_id]);
        links[link_id]->connect(nodes[i][j], nodes[i+1][j]);
        ++link_id;
      }
      if(i>0)
      {
        links[link_id] = new CGRALink(link_id);
        nodes[i][j]->attachOutLink(links[link_id]);
        nodes[i-1][j]->attachInLink(links[link_id]);
        links[link_id]->connect(nodes[i][j], nodes[i-1][j]);
        ++link_id;
      }
      if(j<columns-1)
      {
        links[link_id] = new CGRALink(link_id);
        nodes[i][j]->attachOutLink(links[link_id]);
        nodes[i][j+1]->attachInLink(links[link_id]);
        links[link_id]->connect(nodes[i][j], nodes[i][j+1]);
        ++link_id;
      }
      if(j>0)
      {
        links[link_id] = new CGRALink(link_id);
        nodes[i][j]->attachOutLink(links[link_id]);
        nodes[i][j-1]->attachInLink(links[link_id]);
        links[link_id]->connect(nodes[i][j], nodes[i][j-1]);
        ++link_id;
      }
    }
  }
}

int CGRA::getFUCount()
{
  return FUCount;
}

void CGRA::constructMRRG(int II)
{
  for(int i=0; i<rows; ++i)
    for(int j=0; j<columns; ++j)
      nodes[i][j]->constructMRRG(FUCount, II);

  for(int i=0; i<LinkCount; ++i)
    links[i]->constructMRRG(FUCount, II);
}

CGRALink* CGRA::getLink(CGRANode* n1, CGRANode* n2)
{
   for(int i=0; i<LinkCount; ++i)
   {
     if(links[i]->getConnectedNode(n1) == n2 and links[i]->getConnectedNode(n2) == n1)
     {
       return links[i];
     }
  }
  errs() << "bad quiry for CGRA link\n";
  return NULL;
//  assert(0);
}

