#include "Mapper.h"
#include <cmath>

int Mapper::getResMII(DFG* dfg, CGRA* cgra)
{
  int ResMII = ceil(float(dfg->getNodeCount()) / cgra->getFUCount());
  return ResMII;
}

int Mapper::getRecMII(DFG* dfg)
{
  float RecMII = 0.0;
  float temp_RecMII = 0.0;
  list<list<DFG::Edge>> cycles = dfg->getCycles();
  // TODO: RecMII = MAX (delay(c) / distance(c))
  for( list<list<DFG::Edge>>::iterator cycle=cycles.begin(); cycle!=cycles.end(); ++cycle)
  {
    temp_RecMII = float(cycle->size()) / 1.0;
    if(temp_RecMII > RecMII)
      RecMII = temp_RecMII;
  }
  return ceil(RecMII);
}

void Mapper::constructMRRG(CGRA* cgra, int II)
{
  mapping.clear();
  mapping_timing.clear();
  cgra->constructMRRG(II);  
  maxMappingCycle = cgra->getFUCount()*II*II;
}

// TODO: assume that the arriving data can stay inside the input buffer
map<CGRANode*, int> Mapper::dijkstra_search(CGRA* cgra, DFG* dfg, DFG_Node srcDFGNode, CGRANode* dstCGRANode)
{
  list<CGRANode*> search_pool;
  map<CGRANode*, int> distance;
  map<CGRANode*, int> timing;
  map<CGRANode*, CGRANode*> previous;
//  errs()<<"DEBUG -1, srcDFGNode: "<<*(srcDFGNode.first)<<"; CGRANode: "<<mapping[srcDFGNode]->getID()<<"\n";
  timing[mapping[srcDFGNode]] = mapping_timing[srcDFGNode];
  for(int i=0; i<cgra->getRows(); ++i) {
    for (int j=0; j<cgra->getColumns(); ++j) {
      CGRANode* node = cgra->nodes[i][j];
      distance[node] = MAX_COST;
      timing[node] = mapping_timing[srcDFGNode];
      // TODO: should also consider the xbar here?
      if (!cgra->nodes[i][j]->canOccupyFU(timing[node])) {
        int temp_cycle = timing[node];
        timing[node] = MAX_COST;
        while (temp_cycle < MAX_COST) {
          if (cgra->nodes[i][j]->canOccupyFU(temp_cycle)) {
            timing[node] = temp_cycle;
            break;
          }
          ++temp_cycle;
        }
      }
      previous[node] = NULL;
      search_pool.push_back(cgra->nodes[i][j]);
    }
  }
//  errs()<<"DEBUG see timing[mapping[srcDFGNode]] + 1: "<<timing[mapping[srcDFGNode]] + 1<<"\n";
//  errs()<<"DEBUG see mapping_timg[srcDFGNode]]: "<<mapping_timing[srcDFGNode]<<"\n";
//  errs()<<"DEBUG see srcDFGNode: "<<*srcDFGNode.first<<"\n";
//  errs()<<"---------\n";
  distance[mapping[srcDFGNode]] = 0;
  while (search_pool.size()!=0) {
    int min_cost = MAX_COST + 1;
    CGRANode* min_node;
    for (list<CGRANode*>::iterator current_node=search_pool.begin(); current_node!=search_pool.end(); ++current_node) {
      if (distance[*current_node] < min_cost) {
        min_cost = distance[*current_node];
        min_node = *current_node;
      }
    }
    assert(min_node != NULL);
    search_pool.remove(min_node);
    // found the target point in the shortest path
    if (min_node == dstCGRANode) {
        timing[dstCGRANode] = min_node->getMinIdleCycle(timing[min_node]);
      break;
    }
    list<CGRANode*> current_neighbors = min_node->getOutNeighbors();
    int temp_cycle = timing[min_node];
    for (list<CGRANode*>::iterator neighbor=current_neighbors.begin(); neighbor!=current_neighbors.end(); ++neighbor) {
      int cycle = temp_cycle;
      while (1) {
        CGRALink* current_link = min_node->getOutLink(*neighbor);
        // TODO: should also consider the cost of the register file
        // if(!current_link->isOccupied(cycle) and !(*neighbor)->canOccupyFU(cycle))
        if (!current_link->isOccupied(cycle) and min_node->canOccupyXbar(current_link, cycle)) {
          // rough estimate the cost based on the suspend cycle
          int cost = distance[min_node] + (cycle - timing[min_node]) + 1;
          if(cost < distance[*neighbor])
          {
            distance[*neighbor] = cost;
            timing[*neighbor] = cycle;
            previous[*neighbor] = min_node;
          }
          break;
        }
        ++cycle;
        if(cycle > MAX_COST)
          break;
      }
    }
  }

  // map the shortest path
  map<CGRANode*, int> path;
  CGRANode* u = dstCGRANode;
  if(previous[u] != NULL or u == mapping[srcDFGNode])
  {
    while(u != NULL)
    {
      path[u] = timing[u];
      u = previous[u];
    }
  }
  if(timing[dstCGRANode] > maxMappingCycle) {
    path.clear();
    return path;
  }
//  errs()<<"DEBUG see the last cycle: "<<timing[dstCGRANode]<<"\n";
  return path;
}

//CGRANode* Mapper::getMappedCGRANode(DFG_Node dfg_node)
//{
//  return mapping[dfg_node];
//}
//
//int Mapper::getMappedCGRANodeTiming(DFG_Node dfg_node)
//{
//  return mapping_timing[dfg_node];
//}

map<CGRANode*, int> Mapper::getPathWithMinCost(list<map<CGRANode*, int>> paths) {
  int min_cost = MAX_COST + 1;
  map<CGRANode*, int> path;
  for(list<map<CGRANode*, int>>::iterator pa=paths.begin(); pa!=paths.end(); ++pa) {
    map<int, CGRANode*> reorder_path;
    for(map<CGRANode*, int>::iterator rpa=pa->begin(); rpa!=pa->end(); ++rpa)
      reorder_path[(*rpa).second] = (*rpa).first;

    map<int, CGRANode*>::reverse_iterator iter=reorder_path.rbegin();
    if((*iter).first < min_cost) {
      path = *pa;
      min_cost = (*iter).first;
      assert(min_cost == path[(*iter).second]);
      // TODO: move this part of logic into "calculateCost()" and return 'pair' struct.
      min_cost += ((*iter).second)->getCurrentCtrlMemItems();
    }
  }
  return path;
}

// TODO: will grant award for the overuse the same link for the same data delivery
map<CGRANode*, int> Mapper::calculateCost(CGRA* cgra, DFG* dfg, DFG_Node dfg_node, CGRANode* fu) {
  map<CGRANode*, int> path;
  list<DFG_Node> predNodes = dfg->getPredNodes(dfg_node);
  int latest = 0;
  bool isAnyPredDFGNodeMapped = false;
  for(list<DFG_Node>::iterator pre=predNodes.begin(); pre!=predNodes.end(); ++pre) {
    if(mapping.find(*pre) != mapping.end()) {
      // leverage Dijkstra algorithm to search the shortest path between 
      // the mapped 'CGRANode' of the 'pre' and the target 'fu'
      map<CGRANode*, int> temp_path = dijkstra_search(cgra, dfg, *pre, fu);
      if(temp_path[fu] > latest) {
        latest = temp_path[fu];
        path = temp_path;
      }
      isAnyPredDFGNodeMapped = true;
    }
  }
  // TODO: should not be any CGRA node, should consider the memory access.
  // A dfg node can be mapped onto any CGRA Node if no predecessor of it has
  // been mapped.
  if (!isAnyPredDFGNodeMapped) {
    int cycle = 0;
    while (cycle < MAX_COST) {
      for (int i=0; i<cgra->getRows(); ++i) {
        for (int j=0; j<cgra->getColumns(); ++j) {
          if (cgra->nodes[i][j]->canOccupyFU(cycle)) {
            path[cgra->nodes[i][j]] = cycle;
            return path;
          }
        }
      }
      ++cycle;
    }
    errs() << "failed in mapping the starting dfg node\n";
  }
  return path;
}

// schedule is based on the modulo II,
// the 'path' contains one predecessor can be definitely mapped,
// but the pathes containing other predecessors have possibility 
// to fail in mapping.
bool Mapper::schedule(CGRA* cgra, DFG* dfg, int II, DFG_Node dfg_node, map<CGRANode*, int> path) {
  map<int, CGRANode*> reorder_path;
  for (map<CGRANode*, int>::iterator iter=path.begin(); iter!=path.end(); ++iter) {
    reorder_path[(*iter).second] = (*iter).first;
  }
  map<int, CGRANode*>::reverse_iterator ri = reorder_path.rbegin();
  CGRANode* fu = (*ri).second;
  errs()<<"schedule dfg node["<<*(dfg_node.first)<<"] onto fu["<<fu->getID()<<"] at cycle "<<path[fu]<<"\n";
  // map the dfg node onto cgra node with timing
  mapping[dfg_node] = fu;
  fu->setOpt(dfg_node, path[fu], II);
  mapping_timing[dfg_node] = path[fu];

  CGRANode* onePredCGRANode;
  map<int, CGRANode*>::iterator last_iter;
  for (map<int, CGRANode*>::iterator iter=reorder_path.begin(); iter!=reorder_path.end(); ++iter) {
    if (iter != reorder_path.begin()) {
      CGRALink* l = cgra->getLink((*last_iter).second, (*iter).second);
      l->occupy((*iter).first, II);
    } else {
      onePredCGRANode = (*iter).second;
    }
    last_iter = iter;
  }
  // try to map the path with other predecessors,
  // should consider the timing (two branches should joint at the same time)
  list<DFG_Node> pre_nodes = dfg->getPredNodes(dfg_node);
  for (list<DFG_Node>::iterator iter=pre_nodes.begin(); iter!=pre_nodes.end(); ++iter) {
//    errs()<<"DEBUG in loop of pre_nodes about tryToRoute()\n";
    if (mapping.find(*iter) != mapping.end() and mapping[(*iter)] != onePredCGRANode) {
//      errs()<<"DEBUG mapped pre DFG node: "<<*((*iter).first)<<"\n";
//      errs()<<"DEBUG mapped pre CGRA node: "<<mapping[(*iter)]->getID()<<"\n";
//      errs()<<"DEBUG mapped pre timing: "<<mapping_timing[(*iter)]<<"\n";
      if (!tryToRoute(cgra, II, *iter, mapping[*iter], fu))
        return false;
    }
  }
  return true;
}

int Mapper::getMaxMappingCycle() {
  return maxMappingCycle;
}

void Mapper::showSchedule(CGRA* cgra, DFG* dfg, int II) {
  // TODO: display the mapping and routing with timing
  int cycle = 0;
  while (cycle <= cgra->getFUCount()) {
    errs()<<"------------ cycle:"<<cycle<<" -------------\n";
    for (int i=0; i<cgra->getRows(); ++i) {
      for (int j=0; j<cgra->getColumns(); ++j) {
        int occupied = false;
        DFG_Node dfgNode;
        for (list<DFG_Node>::iterator dfgNodeItr=dfg->nodes.begin(); dfgNodeItr!=dfg->nodes.end(); ++dfgNodeItr) {
          if (mapping_timing[*dfgNodeItr] == cycle and mapping[*dfgNodeItr] == cgra->nodes[i][j]) {
            occupied = true;
            dfgNode = *dfgNodeItr;
            break;
          } else if (mapping[*dfgNodeItr] == cgra->nodes[i][j]) {
            int temp_cycle = cycle - II;
            if(temp_cycle == 0 and dfg->getID(*dfgNodeItr) == 1) {
            }
            while (temp_cycle >= 0) {
              if (mapping_timing[*dfgNodeItr] == temp_cycle) {
                occupied = true;
                dfgNode = *dfgNodeItr;
                break;
              }
              temp_cycle -= II;
            }
          }
        }
        if (occupied) {
          if (dfg->getID(dfgNode) < 10)
            errs()<<"[  "<<dfg->getID(dfgNode)<<"  ]  ";
          else
            errs()<<"[ "<<dfg->getID(dfgNode)<<"  ]  ";
        } else {
          errs()<<"[     ]  ";
        }
        if (j == cgra->getColumns() - 1)
          errs()<<"\n";
//        errs()<<"DFG node ["<<dfg->getID(*dfgNodeItr)<<"] on CGRA node ["<<mapping[*dfgNodeItr]->getID()<<"] on cycle "<<mapping_timing[*node]<<"\n";
      }
    }
    ++cycle;
  }
  errs()<<"II: "<<II<<"\n";
}

// TODO: Assume that the arriving data can stay inside the input buffer.
// TODO: Should traverse from dst to src?
// TODO: Should consider the unmapped predecessors.
// TODO: Should consider the type of CGRA, say, a static in-elastic CGRA should
//       join at the same successor at exact same cycle without pending.
bool Mapper::tryToRoute(CGRA* cgra, int II, DFG_Node srcDFGNode, CGRANode* srcCGRANode, CGRANode* dstCGRANode) {
  list<CGRANode*> search_pool;
  map<CGRANode*, int> distance;
  map<CGRANode*, int> timing;
  map<CGRANode*, CGRANode*> previous;
  timing[srcCGRANode] = mapping_timing[srcDFGNode];
  for (int i=0; i<cgra->getRows(); ++i) {
    for (int j=0; j<cgra->getColumns(); ++j) {
      CGRANode* node = cgra->nodes[i][j];
      distance[node] = MAX_COST;
      timing[node] = timing[srcCGRANode] + 1;
      // TODO: should also consider the xbar here?
//      if (!cgra->nodes[i][j]->canOccupyFU(timing[node])) {
//        int temp_cycle = timing[node];
//        timing[node] = MAX_COST;
//        while (temp_cycle < MAX_COST) {
//          if (cgra->nodes[i][j]->canOccupyFU(temp_cycle)) {
//            timing[node] = temp_cycle;
//            break;
//          }
//          ++temp_cycle;
//        }
//      }
      previous[node] = NULL;
      search_pool.push_back(cgra->nodes[i][j]);
    }
  }
  distance[srcCGRANode] = 0;
  while (search_pool.size()!=0) {
    int min_cost = MAX_COST + 1;
    CGRANode* min_node;
    for (list<CGRANode*>::iterator current_node=search_pool.begin(); current_node!=search_pool.end(); ++current_node) {
      if (distance[*current_node] < min_cost) {
        min_cost = distance[*current_node];
        min_node = *current_node;
      }
    }
    search_pool.remove(min_node);
    // found the target point in the shortest path
    if (min_node == dstCGRANode) {
//      timing[dstCGRANode] = min_node->getMinIdleCycle(timing[min_node]);
      break;
    }
    list<CGRANode*> current_neighbors = min_node->getOutNeighbors();
    for (list<CGRANode*>::iterator neighbor=current_neighbors.begin(); neighbor!=current_neighbors.end(); ++neighbor) {
      int cycle = timing[min_node];
      while (1) {
        CGRALink* current_link = min_node->getOutLink(*neighbor);
        // TODO: should also consider the cost of the register file
        // if(!current_link->isOccupied(cycle) and !(*neighbor)->canOccupyFU(cycle))
        if(!current_link->isOccupied(cycle) and min_node->canOccupyXbar(current_link, cycle)) {
          // rough estimate the cost based on the suspend cycle
          int cost = distance[min_node] + (cycle - timing[min_node]);
          if(cost < distance[*neighbor]) {
            distance[*neighbor] = cost + 1;
            timing[*neighbor] = cycle;
            previous[*neighbor] = min_node;
          }
          break;
        }
        ++cycle;
        if(cycle > MAX_COST)
          break;
      }
    }
  }

  // Construct the shortest path for routing.
  map<CGRANode*, int> path;
  CGRANode* u = dstCGRANode;
  if (previous[u] != NULL or u == srcCGRANode) {
    while (u != NULL) {
      path[u] = timing[u];
      u = previous[u];
    }
  } else {
    return false;
  }

  // Not a valid mapping if it exceeds the 'maxMappingCycle'.
  if(timing[dstCGRANode] > maxMappingCycle) {
    return false;
  }

  // try to route the data flow
  map<int, CGRANode*> reorder_path;
  for(map<CGRANode*, int>::iterator iter=path.begin(); iter!=path.end(); ++iter) {
    reorder_path[(*iter).second] = (*iter).first;
  }

  map<int, CGRANode*>::iterator last_iter;
  for (map<int, CGRANode*>::iterator iter=reorder_path.begin(); iter!=reorder_path.end(); ++iter) {
    if (iter != reorder_path.begin()) {
      CGRALink* l = cgra->getLink((*last_iter).second, (*iter).second);
      l->occupy((*iter).first, II);
    }
    last_iter = iter;
  }
  return true;
}

