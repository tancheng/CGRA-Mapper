/*
 * ======================================================================
 * Mapper.cpp
 * ======================================================================
 * Mapper implementation.
 *
 * Author : Cheng Tan
 *   Date : July 16, 2019
 */

#include "Mapper.h"
#include "json.hpp"
#include <cmath>
#include <iostream>
#include <string>
#include <list>
#include <map>
#include <vector>
#include <fstream>
#include <omp.h>

//#include <nlohmann/json.hpp>
using json = nlohmann::json;

Mapper::Mapper(bool t_DVFSAwareMapping) {
  m_DVFSAwareMapping = t_DVFSAwareMapping;
}

int Mapper::getResMII(DFG* t_dfg, CGRA* t_cgra) {
  int ResMII = ceil(float(t_dfg->getNodeCount()) / t_cgra->getFUCount());
  // For exclusive strategy, the II max be not less than the maximum execution latency.
  int max_exec_latency = t_dfg->getMaxExecLatency();
  if (!t_cgra->getSupportInclusive() && max_exec_latency > ResMII) ResMII = max_exec_latency;
  return ResMII;
}

int Mapper::getRecMII(DFG* t_dfg) {
  float RecMII = 0.0;
  float temp_RecMII = 0.0;
  list<list<DFGNode*>*>* cycles = t_dfg->getCycleLists(); //calculateCycles();
  // cout<<"... number of cycles: "<<cycles->size()<<" ..."<<endl;
  // TODO: RecMII = MAX (delay(c) / distance(c))
  for( list<DFGNode*>* cycle: *cycles) {
    temp_RecMII = float(cycle->size()) / 1.0;
    // cout << "... [DEBUG] cycle length " << temp_RecMII << "..." <<endl;
    // for (DFGNode* dfgNode: *cycle){
    //   cout << "... [DEBUG] cycle nodes " << dfgNode->getID() << " "<< dfgNode->getOpcodeName() << " ";
    // }
    if(temp_RecMII > RecMII)
      RecMII = temp_RecMII;
  }
  return ceil(RecMII);
}

int Mapper::getExpandableII(DFG* t_dfg, int t_ii) {
  int rec_mii = getRecMII(t_dfg);
  int ceiled = ceil((float)t_ii / 2.0);
  return std::max(rec_mii, ceiled);
}

void Mapper::constructMRRG(DFG* t_dfg, CGRA* t_cgra, int t_II) {
  m_mapping.clear();
  m_mappingTiming.clear();
  t_cgra->constructMRRG(t_II);
  m_maxMappingCycle = t_cgra->getFUCount()*t_II*t_II;
  for (DFGNode* dfgNode: t_dfg->nodes) {
    dfgNode->clearMapped();
  }
}

// The arriving data can stay inside the input buffer
map<CGRANode*, int>* Mapper::dijkstra_search(CGRA* t_cgra, DFG* t_dfg,
    int t_II, DFGNode* t_srcDFGNode, DFGNode* t_targetDFGNode,
    CGRANode* t_dstCGRANode) {
  list<CGRANode*> searchPool;
  map<CGRANode*, int> distance;
  map<CGRANode*, int> timing;
  map<CGRANode*, CGRANode*> previous;
  CGRANode* srcCGRANode = m_mapping[t_srcDFGNode];
  timing[srcCGRANode] = m_mappingTiming[t_srcDFGNode];
  for (int i=0; i<t_cgra->getRows(); ++i) {
    for (int j=0; j<t_cgra->getColumns(); ++j) {
      CGRANode* node = t_cgra->nodes[i][j];
      distance[node] = m_maxMappingCycle;
      timing[node] = m_mappingTiming[t_srcDFGNode];
      timing[node] += t_srcDFGNode->getExecLatency(node->getDVFSLatencyMultiple()) - 1;
//      if (t_srcDFGNode->isLoad() or t_srcDFGNode->isStore()) {
//        timing[node] += 1;
//      }
      // TODO: should also consider the xbar here?
//      if (!cgra->nodes[i][j]->canOccupyFU(timing[node], II)) {
//        int temp_cycle = timing[node];
//        timing[node] = m_maxMappingCycle;
//        while (temp_cycle < m_maxMappingCycle) {
//          if (cgra->nodes[i][j]->canOccupyFU(temp_cycle, II)) {
//            timing[node] = temp_cycle;
//            break;
//          }
//          ++temp_cycle;
//        }
//      }
      previous[node] = NULL;
      searchPool.push_back(t_cgra->nodes[i][j]);
    }
  }
  distance[m_mapping[t_srcDFGNode]] = 0;
  while (searchPool.size() != 0) {
    int minCost = m_maxMappingCycle + 1;
    CGRANode* minNode;
    for (CGRANode* currentNode: searchPool) {
      if (distance[currentNode] < minCost) {
        minCost = distance[currentNode];
        minNode = currentNode;
      }
    }
    assert(minNode != NULL);
    searchPool.remove(minNode);
    // found the target point in the shortest path
    if (minNode == t_dstCGRANode) {
      timing[t_dstCGRANode] = minNode->getMinIdleCycle(t_targetDFGNode, timing[minNode], t_II);
      break;
    }
    list<CGRANode*>* currentNeighbors = minNode->getNeighbors();
//    cout<<"DEBUG no need?"<<endl;

    for (CGRANode* neighbor: *currentNeighbors) {
      int cycle = timing[minNode];
      while (1) {
        CGRALink* currentLink = minNode->getOutLink(neighbor);
        // TODO: should also consider the cost of the register file
        if (currentLink->canOccupy(t_srcDFGNode, srcCGRANode, cycle, t_II)) {
          // rough estimate the cost based on the suspend cycle
          int cost = distance[minNode] + (cycle - timing[minNode]) + 1;
          if (cost < distance[neighbor]) {
            distance[neighbor] = cost;
            timing[neighbor] = cycle + 1;
            previous[neighbor] = minNode;
          }
          break;
        }
        ++cycle;
        if(cycle > m_maxMappingCycle)
          break;
      }
    }
  }

  // Get the shortest path.
  map<CGRANode*, int>* path = new map<CGRANode*, int>();
  CGRANode* u = t_dstCGRANode;
  if (previous[u] != NULL or u == m_mapping[t_srcDFGNode]) {
    while (u != NULL) {
      (*path)[u] = timing[u];
      u = previous[u];
    }
  }
  if (timing[t_dstCGRANode] > m_maxMappingCycle or
      !t_dstCGRANode->canOccupy(t_targetDFGNode,
      timing[t_dstCGRANode], t_II)) {
//    path.clear();
    delete path;
    return NULL;
  }
  return path;
}

list<map<CGRANode*, int>*>* Mapper::getOrderedPotentialPaths(CGRA* t_cgra,
    DFG* t_dfg, int t_II, DFGNode* t_dfgNode, list<map<CGRANode*, int>*>* t_paths) {
  map<map<CGRANode*, int>*, float>* pathsWithCost =
      new map<map<CGRANode*, int>*, float>();
  for (list<map<CGRANode*, int>*>::iterator path=t_paths->begin();
      path!=t_paths->end(); ++path) {
    if ((*path)->size() == 0)
      continue;

    map<int, CGRANode*>* reorderPath = getReorderPath(*path);
//    for (map<CGRANode*, int>::iterator rp=(*path)->begin(); rp!=(*path)->end(); ++rp)
//      reorderPath[(*rp).second] = (*rp).first;
//    assert(reorderPath.size() == (*path)->size());

    map<int, CGRANode*>::reverse_iterator riter=reorderPath->rbegin();

    int distanceCost = (*riter).first;
    CGRANode* targetCGRANode = (*riter).second;
    int targetCycle = (*riter).first;
    if (distanceCost >= m_maxMappingCycle)
      continue;
//    if (t_dfgNode->getID() == 2 or t_dfgNode->getID() == 1) {
//      cout<<"DEBUG what?! distance: "<<distanceCost<<"; target CGRA node: "<<targetCGRANode->getID()<<endl;
//    }
    // Consider the cost of the distance.
    float cost = distanceCost + 1;

    // Consider the same tile mapped with continuously two DFG nodes.
    map<int, CGRANode*>::iterator lastCGRANodeItr=reorderPath->begin();
    for (map<int, CGRANode*>::iterator cgraNodeItr=reorderPath->begin();
        cgraNodeItr!=reorderPath->end(); ++cgraNodeItr) {
      if (cgraNodeItr != reorderPath->begin()) {
        int lastCycle = (*lastCGRANodeItr).first;
        int currentCycle = (*cgraNodeItr).first;
        int delta = currentCycle - lastCycle;
        if (delta > 1) {
          cost = cost + 1.5;
        }
      }
      lastCGRANodeItr = cgraNodeItr;
    }

    // Consider the single tile that processes everything. FIXME: this is
    // actually a bug because we use map<CGRANode*, int> rather than
    // map<int, CGRANode*>, in which case the different cycles's execution
    // will be wrongly merged into one.
    if (reorderPath->size() == 1) {
      cost += 2;
    }

    // Consider the cost of the utilization of contrl memory.
    if (m_DVFSAwareMapping) {
      cost += targetCGRANode->getCurrentCtrlMemItems() / 2;
    } else {
      cost += targetCGRANode->getCurrentCtrlMemItems();
    }

    // Consider the cost of the outgoing ports.
    if (t_dfgNode->getSuccNodes()->size() > 1) {
      cost += 4 - targetCGRANode->getOutLinks()->size() +
          abs(t_cgra->getColumns()/2-targetCGRANode->getX()) +
          abs(t_cgra->getRows()/2-targetCGRANode->getY());
    }
    if (t_dfgNode->getPredNodes()->size() > 0) {
      list<DFGNode*>* tempPredNodes = t_dfgNode->getPredNodes();
      for (DFGNode* predDFGNode: *tempPredNodes) {
        if (predDFGNode->getSuccNodes()->size() > 2
            and m_mapping.find(predDFGNode) != m_mapping.end()) {
          if (m_mapping[predDFGNode] == targetCGRANode)
            cost -= 0.5;
        }
      }
    }

    // Considers the island for DVFS.
    // Better to put the DFGNode inside the CGRA island with the
    // matched DVFS level. A special case is by default the DVFS
    // level is 1, but the island mapped with DFG node has the
    // real DVFS level 1, which has the highest priority. The unmapped
    // island has lower priority though its DVFS level is also shown
    // as 1.
    if (m_DVFSAwareMapping) {
      if (targetCGRANode->isMapped()) {
        cost -= 0.3;
      }
      if (targetCGRANode->isSynced() and
          targetCGRANode->getDVFSLatencyMultiple() == t_dfgNode->getDVFSLatencyMultiple()) {
        cost -= 1.0;
      } else if (!targetCGRANode->isSynced()) {
        cost -= 0.2;
      }
    }

    /*
    // Prefer to map the DFG nodes from left to right rather than
    // always picking CGRA node at left.
    if (t_dfgNode->getPredNodes()->size() > 0) {
      list<DFGNode*>* tempPredNodes = t_dfgNode->getPredNodes();
      for (DFGNode* predDFGNode: *tempPredNodes) {
        if (m_mapping.find(predDFGNode) != m_mapping.end()) {
          if (m_mapping[predDFGNode]->getX() > targetCGRANode->getX() or
              m_mapping[predDFGNode]->getY() > targetCGRANode->getY()) {
            cost += 0.5;
          }
        }
      }
    }
    */

    // Consider the cost of that the DFG node with multiple successor
    // might potentially occupy the surrounding CGRA nodes.
    list<CGRANode*>* neighbors = targetCGRANode->getNeighbors();
    for (CGRANode* neighbor: *neighbors) {
      list<DFGNode*>* dfgNodes = getMappedDFGNodes(t_dfg, neighbor);
      for (DFGNode* dfgNode: *dfgNodes) {
        if (dfgNode->getSuccNodes()->size() > 2) {
          cost += 0.4;
        }
      }
    }

    // Consider the cost of occupying the leftmost (rightmost) CGRA
    // nodes that are reserved for load.
    if ((!t_dfgNode->isLoad() and targetCGRANode->canLoad()) or
        (!t_dfgNode->isStore() and targetCGRANode->canStore())) {
      cost += 2;
    }

    // Consider the bonus of reusing the same link for delivery the
    // same data to different destination CGRA nodes (multicast).
    lastCGRANodeItr=reorderPath->begin();
    for (map<int, CGRANode*>::iterator cgraNodeItr=reorderPath->begin();
        cgraNodeItr!=reorderPath->end(); ++cgraNodeItr) {
      if (cgraNodeItr != reorderPath->begin()) {
        CGRANode* left = (*lastCGRANodeItr).second;
        CGRANode* right = (*cgraNodeItr).second;
        int leftCycle = (*lastCGRANodeItr).first;
//        cout<<"$$$$$$$$$$ wrong?! left node: "<<left->getID()<<" -> right node: "<<right->getID()<<endl;
        CGRALink* l = left->getOutLink(right);
        if (l != NULL and l->isReused(leftCycle)) {
          cost -= 0.5;
        }
      }
      lastCGRANodeItr = cgraNodeItr;
    }

    // Consider the bonus of available links on the target CGRA nodes.
    cost -= targetCGRANode->getOccupiableInLinks(targetCycle, t_II)->size()*0.3 +
        targetCGRANode->getOccupiableOutLinks(targetCycle, t_II)->size()*0.3;

    (*pathsWithCost)[*path] = cost;
  }

  list<map<CGRANode*, int>*>* potentialPaths = new list<map<CGRANode*, int>*>();
  while(pathsWithCost->size() != 0) {
    float minCost = (*pathsWithCost->begin()).second;
    map<CGRANode*, int>* currentPath = (*pathsWithCost->begin()).first;
    for (map<map<CGRANode*, int>*, float>::iterator pathItr=pathsWithCost->begin();
        pathItr!=pathsWithCost->end(); ++pathItr) {
      if ((*pathItr).second < minCost) {
        minCost = (*pathItr).second;
        currentPath = (*pathItr).first;
      }
    }
    pathsWithCost->erase(currentPath);
    potentialPaths->push_back(currentPath);
  }

  delete pathsWithCost;
  return potentialPaths;
}

map<CGRANode*, int>* Mapper::getPathWithMinCostAndConstraints(CGRA* t_cgra,
    DFG* t_dfg, int t_II, DFGNode* t_dfgNode, list<map<CGRANode*, int>*>* t_paths) {

  list<map<CGRANode*, int>*>* potentialPaths =
      getOrderedPotentialPaths(t_cgra, t_dfg, t_II, t_dfgNode, t_paths);

  // The paths are already ordered well based on the cost in getPotentialPaths().
  list<map<CGRANode*, int>*>::iterator pathItr=potentialPaths->begin();
  return (*pathItr);
}

list<DFGNode*>* Mapper::getMappedDFGNodes(DFG* t_dfg, CGRANode* t_cgraNode) {
  list<DFGNode*>* dfgNodes = new list<DFGNode*>();
  for (DFGNode* dfgNode: t_dfg->nodes) {
    if (m_mapping.find(dfgNode) != m_mapping.end())
      if ( m_mapping[dfgNode] == t_cgraNode)
        dfgNodes->push_back(dfgNode);
  }
  return dfgNodes;
}

// TODO: will grant award for the overuse the same link for the
//       same data delivery
map<CGRANode*, int>* Mapper::calculateCost(CGRA* t_cgra, DFG* t_dfg,
    int t_II, DFGNode* t_dfgNode, CGRANode* t_fu) {
  //cout<<"...calculateCost() for dfgNode "<<t_dfgNode->getID()<<" on tile "<<t_fu->getID()<<endl;
  map<CGRANode*, int>* path = NULL;
  list<DFGNode*>* predNodes = t_dfgNode->getPredNodes();
  int latest = -1;
  bool isAnyPredDFGNodeMapped = false;

  for(DFGNode* pre: *predNodes) {
//      cout<<"[DEBUG] how dare to pre node: "<<pre->getID()<<"; CGRA node: "<<t_fu->getID()<<endl;
    if(m_mapping.find(pre) != m_mapping.end()) {
      // Leverage Dijkstra algorithm to search the shortest path between
      // the mapped 'CGRANode' of the 'pre' and the target 'fu'.
      map<CGRANode*, int>* tempPath = NULL;
      if (t_fu->canSupport(t_dfgNode))
        tempPath = dijkstra_search(t_cgra, t_dfg, t_II, pre,
            t_dfgNode, t_fu);
      if (tempPath == NULL)
        return NULL;
      else if ((*tempPath)[t_fu] >= m_maxMappingCycle) {
        delete tempPath;
        return NULL;
      }
      if ((*tempPath)[t_fu] > latest) {
        latest = (*tempPath)[t_fu];
        path = tempPath;
      }
      isAnyPredDFGNodeMapped = true;
    }
  }
  // TODO: should not be any CGRA node, should consider the memory access.
  // TODO  A DFG node can be mapped onto any CGRA node if no predecessor
  //       of it has been mapped.
  // TODO: should also consider the current config mem iterms.
  if (!isAnyPredDFGNodeMapped) {
    if (!t_fu->canSupport(t_dfgNode))
      return NULL;
    int cycle = 0;
    while (cycle < m_maxMappingCycle) {
      if (t_fu->canOccupy(t_dfgNode, cycle, t_II)) {
        path = new map<CGRANode*, int>();
        (*path)[t_fu] = cycle;
        //cout<<"DEBUG how dare to map DFG node: "<<t_dfgNode->getID()<<"; CGRA node: "<<t_fu->getID()<<" at cycle "<< cycle<<endl;
        return path;
      }
      ++cycle;
    }
//    cout << "DEBUG: failed in mapping the starting DFG node "<<t_dfg->getID(t_dfgNode)<<" on CGRA node "<<t_fu->getID()<<endl;
  }
//  cout<<".....in calculate cost path"<<endl;
//  for (map<CGRANode*, int>::iterator iter=path->begin();
//        iter!=path->end(); ++iter) {
//    cout<<"(tile:"<<(*iter).first->getID()<<", cycle:"<<(*iter).second<<") --";
//  }
//  cout<<endl;
  return path;
}

// Schedule is based on the modulo II, the 'path' contains one
// predecessor that can be definitely mapped, but the pathes
// containing other predecessors have possibility to fail in mapping.
bool Mapper::schedule(CGRA* t_cgra, DFG* t_dfg, int t_II,
    DFGNode* t_dfgNode, map<CGRANode*, int>* t_path, bool t_isStaticElasticCGRA) {

  map<int, CGRANode*>* reorderPath = getReorderPath(t_path);
//
//  // Since cycle on path increases gradually, re-order will not miss anything.
//  for (map<CGRANode*, int>::iterator iter=t_path->begin(); iter!=t_path->end(); ++iter)
//    reorderPath[(*iter).second] = (*iter).first;
//  assert(reorderPath.size() == t_path->size());

  map<int, CGRANode*>::reverse_iterator ri = reorderPath->rbegin();
  CGRANode* fu = (*ri).second;
  cout<<"[DEBUG] schedule dfg node["<<t_dfg->getID(t_dfgNode)<<"] onto fu["<<fu->getID()<<"] at cycle "<<(*t_path)[fu]<<" within II: "<<t_II<<endl;

  // Map the DFG node onto the CGRA nodes across cycles.
  m_mapping[t_dfgNode] = fu;

  // FIXME: Checks DVFS-related stuff around the canOccupy(). 1. Make sure the same island has
  // the same DVFS level. 2. The level matches the targeting DFG node. 3. Or no DFG node in the
  // island yet.

  // FIXME: Asserts DVFS-related stuff here.
  if (fu->isDVFSEnabled()) {
    // assert(t_dfgNode->getDVFSLatencyMultiple() == fu->getDVFSLatencyMultiple());
  }
  fu->setDFGNode(t_dfgNode, (*t_path)[fu], t_II, t_isStaticElasticCGRA);

  // FIXME: Handles DVFS-related stuff here.
  t_cgra->syncDVFSIsland(fu);

  m_mappingTiming[t_dfgNode] = (*t_path)[fu];

  // Route the dataflow onto the CGRA links across cycles.
  CGRANode* onePredCGRANode;
  int onePredCGRANodeTiming;
  map<int, CGRANode*>::iterator previousIter;
  map<int, CGRANode*>::iterator next;
  if (reorderPath->size() > 0) {
    next = reorderPath->begin();
    if (next != reorderPath->end())
      ++next;
  }
  map<int, CGRANode*>::reverse_iterator riter=reorderPath->rbegin();
  bool generatedOut = true;
  for (map<int, CGRANode*>::iterator iter=reorderPath->begin();
      iter!=reorderPath->end(); ++iter) {
    if (iter != reorderPath->begin()) {
      CGRANode* srcCGRANode = (*(reorderPath->begin())).second;
      int srcCycle = (*(reorderPath->begin())).first;
      CGRALink* l = t_cgra->getLink((*previousIter).second, (*iter).second);

      // Distinguish the bypassed and utilized data delivery on xbar.
      bool isBypass = false;
      int duration = (t_II+((*iter).first-(*previousIter).first)%t_II)%t_II;
      if ((*riter).second != (*iter).second and
          (*previousIter).first+1 == (*iter).first)
        isBypass = true;
      else
        duration = (m_mappingTiming[t_dfgNode]-(*previousIter).first)%t_II;
      l->occupy(srcCGRANode->getMappedDFGNode(srcCycle),
                (*previousIter).first, duration,
                t_II, isBypass, generatedOut, t_isStaticElasticCGRA);
      generatedOut = false;
    } else {
      onePredCGRANode = (*iter).second;
      onePredCGRANodeTiming = (*iter).first;
    }
    previousIter = iter;
  }
  delete reorderPath;

  // Try to route the path with other predecessors.
  // TODO: should consider the timing for static CGRA (two branches should
  //       joint at the same time or the register file size equals to 1)
  for (DFGNode* node: *t_dfgNode->getPredNodes()) {
    if (m_mapping.find(node) != m_mapping.end()) {
      if (m_mapping[(node)] == onePredCGRANode and
          onePredCGRANode->getMappedDFGNode(onePredCGRANodeTiming)==node) {
        cout<<"[DEBUG] skip predecessor routing -- dfgNode: "<<node->getID()<<"\n";
        continue;
      }
//      if (m_mapping[(node)] != onePredCGRANode) {
      if (!tryToRoute(t_cgra, t_dfg, t_II, node, m_mapping[node], t_dfgNode, fu,
          m_mappingTiming[t_dfgNode], false, t_isStaticElasticCGRA)){
        cout<<"DEBUG target DFG node: "<<t_dfgNode->getID()<<" on fu: "<<fu->getID()<<" failed, mapped pred DFG node: "<<node->getID()<<"; return false\n";
        return false;
      }
//    }
    }
  }

  // Try to route the path with the mapped successors that are only in
  // certain cycle.
  for (DFGNode* node: *t_dfgNode->getSuccNodes()) {
    if (m_mapping.find(node) != m_mapping.end()) {
      bool bothNodesInCycle = false;
      if (node->shareSameCycle(t_dfgNode) and
          node->isCritical() and t_dfgNode->isCritical()) {//getCycleID() != -1 and
//          node->isCritical() and t_dfgNode->isCritical() and
//          node->getCycleID() == t_dfgNode->getCycleID()) {
        bothNodesInCycle = true;
      }
      if (!tryToRoute(t_cgra, t_dfg, t_II, t_dfgNode, fu, node, m_mapping[node],
          m_mappingTiming[node], bothNodesInCycle, t_isStaticElasticCGRA)) {
        cout<<"DEBUG target DFG node: "<<t_dfgNode->getID()<<" on fu: "<<fu->getID()<<" failed, mapped succ DFG node: "<<node->getID()<<"; return false\n";
        return false;
      }
    }
  }
  return true;
}

int Mapper::getMaxMappingCycle() {
  return m_maxMappingCycle;
}

void Mapper::showUtilization(CGRA* t_cgra, DFG* t_dfg, int t_II,
		             bool t_isStaticElasticCGRA,
			     bool t_enablePowerGating) {

  // Indicates the busy cycles of the functional units inside the
  // tile.
  map<int, int> tile_fu_busy_cycles;
  // Indicates the busy cycles of the crossbar inside the tile.
  map<int, int> tile_xbar_busy_cycles;;
  // Indicates the busy cycles of both the functional units and
  // crossbar inside the tile. Note that this is not simply the
  // sum of `tile_fu_busy_cycles` and the `tile_xbar_busy_cycles`
  // as both the fu and xbar can be busy at the same cycle.
  map<int, int> tile_overall_busy_cycles;

  map<int, float> tile_fu_utilization;
  map<int, float> tile_xbar_utilization;
  map<int, float> tile_overall_utilization;

  for (int i=0; i<t_cgra->getRows(); ++i) {
    for (int j=0; j<t_cgra->getColumns(); ++j) {
      auto tile = t_cgra->nodes[i][j];
      for (int cycle = 0; cycle < t_II; ++cycle) {
	bool is_tile_busy = false;
        if (t_cgra->nodes[i][j]->isOccupied(cycle, t_II)) {
          if (tile_fu_busy_cycles.find(tile->getID()) ==
	      tile_fu_busy_cycles.end()) {
            tile_fu_busy_cycles[tile->getID()] = 0;
          }
          // Xbar is always busy if the fu is busy. This is because the
	  // output of the fu would always go through the xbar no matter
	  // where is the destination (even towards itself, constrained
	  // by the hardware architecture).
	  // TODO: xbar may not be in busy if the fu is in use with a
	  // multi-cycle non-pipelined execution.
          if (tile_xbar_busy_cycles.find(tile->getID()) ==
	      tile_xbar_busy_cycles.end()) {
            tile_xbar_busy_cycles[tile->getID()] = 0;
          }
          tile_fu_busy_cycles[tile->getID()] += 1;
          tile_xbar_busy_cycles[tile->getID()] += 1;
	  is_tile_busy = true;
        } else {
	  // Don't need to check the out links as out links is the in
	  // links of the destination tiles.
	  for (auto inLink : *(tile->getInLinks())) {
	    if (inLink->isOccupied(cycle, t_II, t_isStaticElasticCGRA)) {
              if (tile_xbar_busy_cycles.find(tile->getID()) ==
    	          tile_xbar_busy_cycles.end()) {
                tile_xbar_busy_cycles[tile->getID()] = 0;
	      }
              tile_xbar_busy_cycles[tile->getID()] += 1;
	      is_tile_busy = true;
	      // Only needs to set the xbar busy once.
	      break;
  	    }
	  }
	}
	// Increments busy cycle of the tile either its fu or xbar
	// is busy.
	if (is_tile_busy) {
          if (tile_overall_busy_cycles.find(tile->getID()) ==
    	      tile_overall_busy_cycles.end()) {
            tile_overall_busy_cycles[tile->getID()] = 0;
	  }
	  tile_overall_busy_cycles[tile->getID()] += 1;
	}
      }
      tile_fu_utilization[tile->getID()] =
        ((float)tile_fu_busy_cycles[tile->getID()]) / t_II;
      tile_xbar_utilization[tile->getID()] =
        ((float)tile_xbar_busy_cycles[tile->getID()]) / t_II;
      tile_overall_utilization[tile->getID()] =
        ((float)tile_overall_busy_cycles[tile->getID()]) / t_II;
    }
  }

//    if (cycle < t_II and t_parameterizableCGRA) {
//      for (int i=0; i<t_cgra->getLinkCount(); ++i) {
//	CGRALink* link = t_cgra->links[i];
//        if (link->isOccupied(cycle, t_II, t_isStaticElasticCGRA)) {
//          string strSrcNodeID = to_string(link->getSrc()->getID());
//          string strDstNodeID = to_string(link->getDst()->getID());
//          if (jsonLinks.find(strSrcNodeID) == jsonLinks.end()) {
//            map<string, vector<int>> jsonLinkDsts;
//            jsonLinks[strSrcNodeID] = jsonLinkDsts;
//          }
//          if (jsonLinks[strSrcNodeID].find(strDstNodeID) == jsonLinks[strSrcNodeID].end()) {
//            vector<int> jsonLinkDstCycles;
//            jsonLinks[strSrcNodeID][strDstNodeID] = jsonLinkDstCycles;
//          }
//          jsonLinks[strSrcNodeID][strDstNodeID].push_back(cycle);
//	}
//      }
//    }

//   // Islandize the CGRA nodes. In the prototype, each set of 2x2 nodes are
//   // grouped as one island. For example, a 4x4 CGRA has 2x2 islands, the
//   // tiles of (0, 2), (0, 3), (1, 2), (1, 3) are viewd as the (0, 1) island.
//   std::map<int, vector<CGRANode>> island_map;
//   constexpr int kIslandDim = 2;
//   for (int i=0; i<t_cgra->getRows(); ++i) {
//     for (int j=0; j<t_cgra->getColumns(); ++j) {
//       auto tile = t_cgra->nodes[i][j];
//       const int tile_x = tile->getX();
//       const int tile_y = tile->getY();
//       const int island_x = tile_x / kIslandDim;
//       const int island_y = tile_y / kIslandDim;
//       auto island_location = std::make_tuple(island_x, island_y);
//
//       if (island_map.find(island_location) != island_map.end()) {
//         island_map[island_location].push_back(*tile);
//       } else {
// 	std::vector<CGRANode> tiles{*tile};
//         island_map[island_location] = tiles;
//       }
//     }
//   }

  // TODO: should ignore the disabled tiles.
  int total_active_tiles = 0;
  for (int tile = 0; tile < t_cgra->getFUCount(); ++tile) {
    if (t_enablePowerGating && tile_overall_utilization[tile] == 0) {
      continue;
    }
    total_active_tiles += 1;
  }
  float avg_tile_overall_utilization = 0.0;
  float max_tile_overall_utilization = 0.0;
  float avg_tile_fu_utilization = 0.0;
  float avg_tile_xbar_utilization = 0.0;
  for (int tile = 0; tile < t_cgra->getFUCount(); ++tile) {
    if (max_tile_overall_utilization < tile_overall_utilization[tile]) {
      max_tile_overall_utilization = tile_overall_utilization[tile];
    }
    avg_tile_overall_utilization += tile_overall_utilization[tile];
    avg_tile_fu_utilization += tile_fu_utilization[tile];
    avg_tile_xbar_utilization += tile_xbar_utilization[tile];
    // cout << "tile[" << tile << "] fu utilization: " << tile_fu_utilization[tile] << "; xbar utilization: " << tile_xbar_utilization[tile] << "; overall utilization: " << tile_overall_utilization[tile] << endl;
  }
  avg_tile_overall_utilization /= total_active_tiles;
  avg_tile_fu_utilization /= total_active_tiles;
  avg_tile_xbar_utilization /= total_active_tiles;
  //max_tile_overall_utilization /= total_active_tiles;

  cout << "tile avg fu utilization: " << avg_tile_fu_utilization*100 << "%; avg xbar utilization: " << avg_tile_xbar_utilization*100 << "%; avg overall utilization: " << avg_tile_overall_utilization*t_II*100 << "%" << endl;
  cout << "max overall utilization: " << max_tile_overall_utilization*t_II*100 << "%" << endl;

  // Collects the histogram of tiles' utilization.
  // Histogram for the number of tiles that have utilization of 0%.
  int tile_count_0 = 0;
  // Histogram for the number of tiles that have utilization in (0%, 25%].
  int tile_count_0_to_25 = 0;
  // Histogram for the number of tiles that have utilization in (25%, 50%].
  int tile_count_25_to_50 = 0;
  // Histogram for the number of tiles that have utilization in (50%, 100%].
  int tile_count_50_to_100 = 0;
  for (int tile = 0; tile < t_cgra->getFUCount(); ++tile) {
    if (tile_overall_utilization[tile] == 0) {
      tile_count_0 += 1;
    } else if (tile_overall_utilization[tile] <= 0.25) {
      tile_count_0_to_25 += 1;
    } else if (tile_overall_utilization[tile] <= 0.5) {
      tile_count_25_to_50 += 1;
    } else {
      tile_count_50_to_100 += 1;
    }
  }

  // Assembles utilization of islands.
  std::map<int, float> island_utilizations;
  for (auto const& island_tiles : t_cgra->getDVFSIslands()) {
    float max_utilization_within_island = 0.0f;
    for (auto tile : island_tiles.second) {
      if (max_utilization_within_island < tile_overall_utilization[tile->getID()]) {
        max_utilization_within_island = tile_overall_utilization[tile->getID()];
      }
    }
    island_utilizations[island_tiles.first] = max_utilization_within_island;
    // std::cout << "island (" << island_tiles.first
    //           << ") utilization: " << max_utilization_within_island << endl;
  }

  // Collects the histogram of islands' utilization.
  // Histogram for the number of islands that have utilization in [0%, 25%].
  int island_count_0_to_25 = 0;
  // Histogram for the number of islands that have utilization in (25%, 50%].
  int island_count_25_to_50 = 0;
  // Histogram for the number of islands that have utilization in (50%, 100%].
  int island_count_50_to_100 = 0;
  for (auto const& island_utilization : island_utilizations) {
    if (island_utilization.second <= 0.25) {
      island_count_0_to_25 += 1;
    } else if (island_utilization.second <= 0.5) {
      island_count_25_to_50 += 1;
    } else {
      island_count_50_to_100 += 1;
    }
  }

  std::cout << "histogram 0% tile utilization: " << tile_count_0 << endl;
  std::cout << "histogram (0%, 25%] tile utilization: " << tile_count_0_to_25 << endl;
  std::cout << "histogram (25%, 50%] tile utilization: " << tile_count_25_to_50 << endl;
  std::cout << "histogram (50%, 100%] tile utilization: " << tile_count_50_to_100 << endl;

  // std::cout << "histogram [0%, 25%] island utilization: " << island_count_0_to_25 << endl;
  // std::cout << "histogram (25%, 50%] island utilization: " << island_count_25_to_50 << endl;
  // std::cout << "histogram (50%, 100%] island utilization: " << island_count_50_to_100 << endl;

  std::map<int, float> island_dvfs_ratio;
  std::map<int, float> tile_dvfs_ratio;
  for (auto const& island_tiles : t_cgra->getDVFSIslands()) {
    float island_ratio = 0.0;
    int unused_tiles = 0;
    for (auto tile : island_tiles.second) {
      float tile_ratio = 0.0;
      bool isMapped = tile->isMapped();
      if (!isMapped) {
        for (auto outLink : *(tile->getOutLinks())) {
          if (outLink->isMapped()) {
  	    isMapped = true;
	    break;
	  }
  	}
      }
      if (!isMapped) {
        for (auto inLink : *(tile->getInLinks())) {
          if (inLink->isMapped()) {
            isMapped = true;
            break;
          }
        }
      }
      if (!isMapped) {
        if (t_enablePowerGating) {
          tile_ratio = 0.0;
	  unused_tiles += 1;
	} else {
          tile_ratio = 0.25;
          // cout << "tile " << tile->getID() << " DVFS multiple: 0; frequency level: 25%" << endl;
	}
      } else {
        tile_ratio = (1.0 / tile->getDVFSLatencyMultiple());
        // cout << "tile " << tile->getID() << " DVFS multiple: " << tile->getDVFSLatencyMultiple() << "; frequency level: " << tile_ratio * 100 << "%" << endl;
      }
      if (tile_ratio > island_ratio) {
        island_ratio = tile_ratio;
      }
    }
    island_dvfs_ratio[island_tiles.first] = island_ratio * (island_tiles.second.size() - unused_tiles) / island_tiles.second.size();

    for (auto tile : island_tiles.second) {
      if (t_enablePowerGating and tile_overall_utilization[tile->getID()] == 0) {
        tile_dvfs_ratio[tile->getID()] = 0;
      } else {
        tile_dvfs_ratio[tile->getID()] = island_ratio;
      }
    }
  }

  // for (auto const& island_ratio : island_dvfs_ratio) {
  //   cout << "island " << island_ratio.first << " frequency level: " << island_ratio.second * 100 << "%" << endl;
  // }

  float avg_tile_dvfs_ratio = 0.0;
  for (auto const& tile_ratio : tile_dvfs_ratio) {
    avg_tile_dvfs_ratio += tile_ratio.second;
    cout << "tile " << tile_ratio.first << " DVFS frequency level: " << tile_ratio.second * 100 << "%" << endl;
  }

  if (avg_tile_dvfs_ratio == 0) {
    if (t_enablePowerGating) {
      cout << "tile average DVFS frequency level: 0%" << endl;
    } else {
      // Indicates DVFS mode is not enabled and no power gating.
      // Then, by default, the DVFS level is 100%.
      cout << "tile average DVFS frequency level: 100%" << endl;
    }
  } else {
    avg_tile_dvfs_ratio /= t_cgra->getFUCount();
    cout << "tile average DVFS frequency level: " << avg_tile_dvfs_ratio * 100 << "%" << endl;
  }

  // Collects the histogram of tiles' frequency ratio.
  // Histogram for the number of tiles that have frequency ratio of 0%.
  int tile_count_dvfs_ratio_0 = 0;
  // Histogram for the number of tiles that have frequency ratio of 25%.
  int tile_count_dvfs_ratio_25 = 0;
  // Histogram for the number of tiles that have frequency ratio of 50%.
  int tile_count_dvfs_ratio_50 = 0;
  // Histogram for the number of tiles that have frequency ratio of 100%.
  int tile_count_dvfs_ratio_100 = 0;
  for (auto const& tile_ratio : tile_dvfs_ratio) {
    if (tile_ratio.second == 0) {
      tile_count_dvfs_ratio_0 += 1;
    } else if (tile_ratio.second <= 0.25) {
      tile_count_dvfs_ratio_25 += 1;
    } else if (tile_ratio.second <= 0.5) {
      tile_count_dvfs_ratio_50 += 1;
    } else {
      tile_count_dvfs_ratio_100 += 1;
    }
  }

  std::cout << "histogram 0% tile DVFS frequency ratio: " << tile_count_dvfs_ratio_0 << endl;
  std::cout << "histogram 25% tile DVFS frequency ratio: " << tile_count_dvfs_ratio_25 << endl;
  std::cout << "histogram 50% tile DVFS frequency ratio: " << tile_count_dvfs_ratio_50 << endl;
  if (avg_tile_dvfs_ratio == 0) {
    // Indicates DVFS mode is not enabled. Then, by default, the DVFS level is 100% for all the tiles.
    // I don't think this will be executed.
    std::cout << "histogram 100% tile DVFS frequency ratio: " << t_cgra->getFUCount() << endl;
  } else {
    std::cout << "histogram 100% tile DVFS frequency ratio: " << tile_count_dvfs_ratio_100 << endl;
  }
}

void Mapper::showSchedule(CGRA* t_cgra, DFG* t_dfg, int t_II,
    bool t_isStaticElasticCGRA, bool t_parameterizableCGRA) {

  // tiles and links are in different formats (only used for
  // parameterizable CGRA, i.e., CGRA-Flow mapping demonstration).
  // tiles[tileID][cycleID][optID]
  // links[srcTileID][dstTileID][cycleID]
  map<string, map<string, vector<int>>> jsonTiles;
  map<string, map<string, vector<int>>> jsonLinks;
  map<string, map<string, map<string, vector<int>>>> jsonTilesLinks;

  int cycle = 0;
  int displayRows = t_cgra->getRows() * 2 - 1;
  int displayColumns = t_cgra->getColumns() * 2;
  string** display = new std::string*[displayRows];
  for (int i=0; i<displayRows; ++i)
    display[i] = new std::string[displayColumns];
  for (int i=0; i<displayRows; ++i) {
    for (int j=0; j<displayColumns; ++j) {
      display[i][j] = "     ";
      if (j == displayColumns - 1)
        display[i][j] = "\n";
    }
  }
  int showCycleBoundary = t_cgra->getFUCount();
  if (showCycleBoundary < 2 * t_II) {
    showCycleBoundary = 2 * t_II;
  }
  if (t_isStaticElasticCGRA)
    showCycleBoundary = t_dfg->getNodeCount();
  while (cycle <= 2*showCycleBoundary) {

    if (cycle < t_II and t_parameterizableCGRA) {
      for (int i=0; i<t_cgra->getLinkCount(); ++i) {
  CGRALink* link = t_cgra->links[i];
        if (link->isOccupied(cycle, t_II, t_isStaticElasticCGRA)) {
          string strSrcNodeID = to_string(link->getSrc()->getID());
          string strDstNodeID = to_string(link->getDst()->getID());
          if (jsonLinks.find(strSrcNodeID) == jsonLinks.end()) {
            map<string, vector<int>> jsonLinkDsts;
            jsonLinks[strSrcNodeID] = jsonLinkDsts;
          }
          if (jsonLinks[strSrcNodeID].find(strDstNodeID) == jsonLinks[strSrcNodeID].end()) {
            vector<int> jsonLinkDstCycles;
            jsonLinks[strSrcNodeID][strDstNodeID] = jsonLinkDstCycles;
          }
          jsonLinks[strSrcNodeID][strDstNodeID].push_back(cycle);
  }
      }
    }

    cout<<"--------------------------- cycle:"<<cycle<<" ---------------------------"<<endl;
    for (int i=0; i<t_cgra->getRows(); ++i) {
      for (int j=0; j<t_cgra->getColumns(); ++j) {

        // Display the CGRA node occupancy.
        bool fu_occupied = false;
        DFGNode* dfgNode;
        for (DFGNode* currentDFGNode: t_dfg->nodes) {
          if (m_mappingTiming[currentDFGNode] == cycle and
              m_mapping[currentDFGNode] == t_cgra->nodes[i][j]) {
            fu_occupied = true;
            dfgNode = currentDFGNode;
            break;
          } else if (m_mapping[currentDFGNode] == t_cgra->nodes[i][j]) {
            int temp_cycle = cycle - t_II;
            while (temp_cycle >= 0) {
              if (m_mappingTiming[currentDFGNode] == temp_cycle) {
                fu_occupied = true;
                dfgNode = currentDFGNode;
                break;
              }
              temp_cycle -= t_II;
            }
          }
        }
        string str_fu;
        if (fu_occupied) {
          if (t_dfg->getID(dfgNode) < 10)
            str_fu = "[  " + to_string(dfgNode->getID()) + "  ]";
          else
            str_fu = "[ " + to_string(dfgNode->getID()) + "  ]";
    string strNodeID = to_string(t_cgra->nodes[i][j]->getID());
    if (t_parameterizableCGRA) {
      if (jsonTiles.find(strNodeID) == jsonTiles.end()) {
              map<string, vector<int>> jsonTileCycleOps;
        jsonTiles[strNodeID] = jsonTileCycleOps;
      }
      vector<int> jsonCycleOp { dfgNode->getID() };
      jsonTiles[strNodeID][to_string(cycle % t_II)] = jsonCycleOp;
    }
        } else {
          str_fu = "[     ]";
        }
        display[i*2][j*2] = str_fu;

        // FIXME: some arrows are not display correctly (e.g., 7).
        // Display the CGRA link occupancy.
        // \u2190: left; \u2191: up; \u2192: right; \u2193: down;
        // \u21c4: left&right; \u21c5: up&down.
        // TODO: [dashed for bypass]
        // \u21e0: left; \u21e1: up; \u21e2: right; \u21e3: down;
        if (i < t_cgra->getRows() - 1) {
          string str_link = "";
          CGRALink* lu = t_cgra->getLink(t_cgra->nodes[i][j], t_cgra->nodes[i+1][j]);
          CGRALink* ld = t_cgra->getLink(t_cgra->nodes[i+1][j], t_cgra->nodes[i][j]);
          if (ld != NULL and ld->isOccupied(cycle, t_II, t_isStaticElasticCGRA) and
              lu != NULL and lu->isOccupied(cycle, t_II, t_isStaticElasticCGRA)) {
            str_link = "   \u21c5 ";
          } else if (ld != NULL and ld->isOccupied(cycle, t_II, t_isStaticElasticCGRA)) {
            if (!ld->isBypass(cycle))
              str_link = "   \u2193 ";
            else
              str_link = "   \u2193 ";
          } else if (lu != NULL and lu->isOccupied(cycle, t_II, t_isStaticElasticCGRA)) {
            if (!lu->isBypass(cycle))
              str_link = "   \u2191 ";
            else
              str_link = "   \u2191 ";
          } else {
            str_link = "     ";
          }
          display[i*2+1][j*2] = str_link;
        }
        if (j < t_cgra->getColumns() - 1) {
          string str_link = "";
          CGRALink* lr = t_cgra->getLink(t_cgra->nodes[i][j], t_cgra->nodes[i][j+1]);
          CGRALink* ll = t_cgra->getLink(t_cgra->nodes[i][j+1], t_cgra->nodes[i][j]);
          if (lr != NULL and lr->isOccupied(cycle, t_II, t_isStaticElasticCGRA) and
              ll != NULL and ll->isOccupied(cycle, t_II, t_isStaticElasticCGRA)) {
            str_link = " \u21c4 ";
          } else if (lr != NULL and lr->isOccupied(cycle, t_II, t_isStaticElasticCGRA)) {
            if (!lr->isBypass(cycle))
              str_link = " \u2192 ";
            else
              str_link = " \u2192 ";
          } else if (ll != NULL and ll->isOccupied(cycle, t_II, t_isStaticElasticCGRA)) {
            if (!ll->isBypass(cycle))
              str_link = " \u2190 ";
            else
              str_link = " \u2190 ";
          } else {
            str_link = "   ";
          }
          display[i*2][j*2+1] = str_link;
        }
      }
    }

    // Display mapping and routing cycle by cycle.
//    for (int i=0; i<displayRows; ++i) {
    for (int i=displayRows-1; i>=0; --i) {
      for (int j=0; j<displayColumns; ++j) {
        cout<<display[i][j];
      }
    }
    ++cycle;
  }
  cout<<"[Mapping II: "<<t_II<<"]"<<endl;

  if (t_parameterizableCGRA) {
    // TODO: make it clean
    jsonTilesLinks["tiles"] = jsonTiles;
    jsonTilesLinks["links"] = jsonLinks;
    json jsonMap(jsonTilesLinks);
    ofstream f("schedule.json", ios_base::trunc | ios_base::out);
    f << jsonMap;
  }
}

void Mapper::generateJSON(CGRA* t_cgra, DFG* t_dfg, int t_II,
    bool t_isStaticElasticCGRA) {
  ofstream jsonFile;
  jsonFile.open("config.json");
  jsonFile<<"[\n";
  if (!t_isStaticElasticCGRA) {

    bool first = true;
    for (int t=0; t<t_II+1; ++t) {
      for (int i=0; i<t_cgra->getRows(); ++i) {
        for (int j=0; j<t_cgra->getColumns(); ++j) {
          CGRANode* currentCGRANode = t_cgra->nodes[i][j];
          DFGNode* targetDFGNode = NULL;
          for (DFGNode* dfgNode: t_dfg->nodes) {
            if (m_mapping[dfgNode] == currentCGRANode and
                currentCGRANode->getMappedDFGNode(t) == dfgNode) {
              targetDFGNode = dfgNode;
              break;
            }
          }
          list<CGRALink*>* inLinks = currentCGRANode->getInLinks();
          list<CGRALink*>* outLinks = currentCGRANode->getOutLinks();
          bool hasInform = false;
          if (targetDFGNode != NULL) {
            hasInform = true;
          } else {
            for (CGRALink* il: *inLinks) {
              if (il->isOccupied(t, t_II, t_isStaticElasticCGRA)) {
                hasInform = true;
                break;
              }
            }
            for (CGRALink* ol: *outLinks) {
              if (ol->isOccupied(t, t_II, t_isStaticElasticCGRA)) {
                hasInform = true;
                break;
              }
            }
          }
          if (!hasInform)
            continue;
          if (first)
            first = false;
          else
            jsonFile<<",\n";

          jsonFile<<"  {\n";
          jsonFile<<"    \"x\"           : "<<j<<",\n";
          jsonFile<<"    \"y\"           : "<<i<<",\n";
          jsonFile<<"    \"cycle\"       : "<<t<<",\n";
          string targetOpt = "OPT_NAH";
          string stringDst[8];
          string predicate_in = "";
          stringDst[0] = "none";
          stringDst[1] = "none";
          stringDst[2] = "none";
          stringDst[3] = "none";
          stringDst[4] = "none";
          stringDst[5] = "none";
          stringDst[6] = "none";
          stringDst[7] = "none";
          int stringDstIndex = 0;

          // Handle predicate based on inports.
          for (CGRALink* il: *inLinks) {
            if (il->isOccupied(t, t_II, t_isStaticElasticCGRA) and
                il->getMappedDFGNode(t)->isPredicater()) {
              if (predicate_in != "") {
                predicate_in += ",";
              }
              if (predicate_in == "") {
                predicate_in = "[";
              }
              predicate_in += to_string(il->getDirectionID(currentCGRANode));
            }
          }
          // Handle predicate based on predecessor. Both the predecessor 'BR' and
          // the current DFG node can be mapped onto the same CGRA node. I only
          // take care the case one successor would be mapped onto the same CGRA
          // node here for now.
          if (targetDFGNode != NULL and targetDFGNode->isPredicater()) {
            for (DFGNode* succNode: *(targetDFGNode->getPredicatees())) {
              if (currentCGRANode->containMappedDFGNode(succNode, t_II)) {
                if (predicate_in == "") {
                  predicate_in = "[4";
                } else {
                  predicate_in += ",4";
                }
                break; // Assume only one predicatee at the same CGRA node.
              }
            }
          }
          if (predicate_in != "") {
            predicate_in += "]";
          }

          // handle function unit's output
          if (targetDFGNode != NULL) {
            targetOpt = targetDFGNode->getJSONOpt();
            // handle funtion unit's outputs for this cycle
            for (CGRALink* ol: *outLinks) {
              if (ol->isOccupied(t, t_II, t_isStaticElasticCGRA) and
                  ol->getMappedDFGNode(t) == targetDFGNode) {
                // FIXME: should support multiple outputs and distinguish them.
                stringDst[ol->getDirectionID(currentCGRANode)] = "4";
              }
            }
          } else {
            targetOpt = "OPT_NAH";
          }

          // handle function unit's inputs for next cycle
          int out_index = 4;
          int max_index = 7;
          for (int reg_index=0; reg_index<4; ++reg_index) {
            int direction = currentCGRANode->getRegsAllocation(t)[reg_index];
            if (direction != -1) {
              stringDst[out_index] = to_string(direction);
            }
            out_index++;
            assert(out_index <= max_index+1);
          }

          jsonFile<<"    \"opt"<<"\"         : \""<<targetOpt<<"\",\n";
          int predicated = 0;
          if (targetDFGNode != NULL and targetDFGNode->isPredicatee()) {
            predicated = 1;
          }
          jsonFile<<"    \"predicate"<<"\"   : "<<predicated<<",\n";
          if (predicate_in != "") {
            jsonFile<<"    \"predicate_in"<<"\": "<<predicate_in<<",\n";
          }

          // handle bypass: need consider next cycle, i.e., t+1
          int next_t = t+1;
          for (CGRALink* ol: *outLinks) {
            if (ol->isOccupied(next_t, t_II, t_isStaticElasticCGRA)) {
              int outIndex = -1;
              outIndex = ol->getDirectionID(currentCGRANode);
              // skip the outport as function unit inport, since they are
              // not regarded as bypass links.
              if (outIndex>=4) continue;
              for (CGRALink* il: *inLinks) {
                for (int t_tmp=next_t-t_II; t_tmp<next_t; ++t_tmp) {
                  if (il->isOccupied(t_tmp, t_II, t_isStaticElasticCGRA) and
                      il->isBypass(t_tmp) and
                      il->getMappedDFGNode(t_tmp) == ol->getMappedDFGNode(next_t)) {
                    cout<<"[DEBUG] inside roi for CGRA node "<<currentCGRANode->getID()<<"...\n";
                    if (il->getMappedDFGNode(t_tmp) == NULL)
                      cout<<"[DEBUG] none..."<<il->getMappedDFGNode(t_tmp)<<"\n";
                    stringDst[outIndex] = to_string(il->getDirectionID(currentCGRANode));//+"; t_tmp: "+to_string(t_tmp)+"; dfg node: " + to_string(il->getMappedDFGNode(t_tmp)->getID());
                  }
                }
              }
            }
          }
          for (int out_index=0; out_index<8; ++out_index) {
            jsonFile<<"    \"out_"<<to_string(out_index)<<"\"       : \""<<stringDst[out_index]<<"\"";
            if (out_index < 7)
              jsonFile<<",\n";
            else
              jsonFile<<"\n";
          }
          jsonFile<<"  }";
        }
      }
    }
    jsonFile<<"\n]\n";
    jsonFile.close();

    return;
  }
  // TODO: should use nop/constant rather than none/self.
  bool first = true;
  for (int i=0; i<t_cgra->getRows(); ++i) {
    for (int j=0; j<t_cgra->getColumns(); ++j) {
      CGRANode* currentCGRANode = t_cgra->nodes[i][j];
      DFGNode* targetDFGNode = NULL;
      for (DFGNode* dfgNode: t_dfg->nodes) {
        if (m_mapping[dfgNode] == currentCGRANode) {
          targetDFGNode = dfgNode;
          break;
        }
      }
      list<CGRALink*>* inLinks = currentCGRANode->getInLinks();
      list<CGRALink*>* outLinks = currentCGRANode->getOutLinks();
      bool hasInform = false;
      if (targetDFGNode != NULL) {
        hasInform = true;
      } else {
        for (CGRALink* il: *inLinks) {
          if (il->isOccupied(0, t_II, t_isStaticElasticCGRA)) {
            hasInform = true;
            break;
          }
        }
        for (CGRALink* ol: *outLinks) {
          if (ol->isOccupied(0, t_II, t_isStaticElasticCGRA)) {
            hasInform = true;
            break;
          }
        }
      }
      if (!hasInform)
        continue;
      if (first)
        first = false;
      else
        jsonFile<<",\n";

      jsonFile<<"  {\n";
      jsonFile<<"    \"x\"         : "<<j<<",\n";
      jsonFile<<"    \"y\"         : "<<i<<",\n";
      string targetOpt = "none";
      string stringSrc[2];
      stringSrc[0] = "self";
      stringSrc[1] = "self";
      string stringDst[5];
      stringDst[0] = "none";
      stringDst[1] = "none";
      stringDst[2] = "none";
      stringDst[3] = "none";
      stringDst[4] = "none";
      int stringDstIndex = 0;
      if (targetDFGNode != NULL) {
        targetOpt = targetDFGNode->getOpcodeName();
        for (CGRALink* il: *inLinks) {
          if (il->isOccupied(0, t_II, t_isStaticElasticCGRA)
              and !il->isBypass(0)) {
            if (targetDFGNode->isBranch() and
                il->getMappedDFGNode(0)->isCmp()) {
              stringSrc[1] = il->getDirection(currentCGRANode);
            } else if (targetDFGNode->isBranch() and
                !il->getMappedDFGNode(0)->isCmp()) {
              stringSrc[0] = il->getDirection(currentCGRANode);
            } else {
              stringSrc[stringDstIndex++] = il->getDirection(currentCGRANode);
            }
          } else if (il->isOccupied(0, t_II, t_isStaticElasticCGRA) and
              il->isBypass(0) and
              il->getMappedDFGNode(0)->isPredecessorOf(targetDFGNode)) {
            // This is the case that the data is used in the CGRA node and
            // also bypassed to the next.
            if (targetDFGNode->isBranch() and
                il->getMappedDFGNode(0)->isCmp()) {
              stringSrc[1] = il->getDirection(currentCGRANode);
            } else if (targetDFGNode->isBranch() and
                !il->getMappedDFGNode(0)->isCmp()) {
              stringSrc[0] = il->getDirection(currentCGRANode);
            } else {
              stringSrc[stringDstIndex++] = il->getDirection(currentCGRANode);
            }
          }
          if (stringDstIndex == 2)
            break;
        }
        stringDstIndex = 0;
        for (CGRALink* ir: *outLinks) {
          if (ir->isOccupied(0, t_II, t_isStaticElasticCGRA)
              and ir->getMappedDFGNode(0) == targetDFGNode) {
            stringDst[stringDstIndex++] = ir->getDirection(currentCGRANode);
          }
        }
      }
      DFGNode* bpsDFGNode = NULL;
      map<string, list<string>> stringBpsSrcDstMap;
      for (CGRALink* il: *inLinks) {
        if (il->isOccupied(0, t_II, t_isStaticElasticCGRA)
            and il->isBypass(0)) {
          bpsDFGNode = il->getMappedDFGNode(0);
          list<string> stringBpsDst;
          for (CGRALink* ir: *outLinks) {
            if (ir->isOccupied(0, t_II, t_isStaticElasticCGRA)
                and ir->getMappedDFGNode(0) == bpsDFGNode) {
              stringBpsDst.push_back(ir->getDirection(currentCGRANode));
            }
          }
          stringBpsSrcDstMap[il->getDirection(currentCGRANode)] = stringBpsDst;
        }
      }
      jsonFile<<"    \"op\"        : \""<<targetOpt<<"\",\n";
      if (targetDFGNode!=NULL and targetDFGNode->isBranch()) {
        jsonFile<<"    \"src_data\"  : \""<<stringSrc[0]<<"\",\n";
        jsonFile<<"    \"src_bool\"  : \""<<stringSrc[1]<<"\",\n";
      } else {
        jsonFile<<"    \"src_a\"     : \""<<stringSrc[0]<<"\",\n";
        jsonFile<<"    \"src_b\"     : \""<<stringSrc[1]<<"\",\n";
      }
      // There are multiple outputs.
      if (targetDFGNode!=NULL and targetDFGNode->isBranch()) {
        jsonFile<<"    \"dst_false\"  : [ ";
      } else {
        jsonFile<<"    \"dst\"       : [ ";
      }
      assert(stringDstIndex < 5);
      if (stringDstIndex > 0) {
        jsonFile<<"\""<<stringDst[0]<<"\"";
        for (int i=1; i<stringDstIndex; ++i) {
          jsonFile<<", \""<<stringDst[i]<<"\"";
        }
      }
      jsonFile<<" ],\n";
      if (targetDFGNode!=NULL and targetDFGNode->isBranch()) {
        jsonFile<<"    \"dst_true\" : \"self\",\n";
      }
      int bpsIndex = 0;
      for (map<string,list<string>>::iterator iter=stringBpsSrcDstMap.begin();
          iter!=stringBpsSrcDstMap.end(); ++iter) {
        jsonFile<<"    \"bps_src"<<bpsIndex<<"\"  : \""<<(*iter).first<<"\",\n";
        // There are multiple bypass outputs.
        jsonFile<<"    \"bps_dst"<<bpsIndex<<"\"  : [ ";
        bool firstBpsDst = true;
        for (string bpsDst: (*iter).second) {
          if (firstBpsDst)
            firstBpsDst = false;
          else
            jsonFile<<",";
          jsonFile<<"\""<<bpsDst<<"\"";
        }
        jsonFile<<" ],\n";
        ++bpsIndex;
      }
      jsonFile<<"    \"dvfs\"      : "<<"\"nominal\""<<"\n";
      jsonFile<<"  }";
    }
  }
  jsonFile<<"\n]\n";
  jsonFile.close();
}

// TODO: Assume that the arriving data can stay inside the input buffer.
// TODO: Should traverse from dst to src?
// TODO: Should consider the unmapped predecessors.
// TODO: Should consider the type of CGRA, say, a static in-elastic CGRA should
//       join at the same successor at exact same cycle without pending.
bool Mapper::tryToRoute(CGRA* t_cgra, DFG* t_dfg, int t_II,
    DFGNode* t_srcDFGNode, CGRANode* t_srcCGRANode, DFGNode* t_dstDFGNode,
    CGRANode* t_dstCGRANode, int t_dstCycle, bool t_isBackedge,
    bool t_isStaticElasticCGRA) {
  cout<<"[DEBUG] tryToRoute -- srcDFGNode: "<<t_srcDFGNode->getID()<<", srcCGRANode: "<<t_srcCGRANode->getID()<<"; dstDFGNode: "<<t_dstDFGNode->getID()<<", dstCGRANode: "<<t_dstCGRANode->getID()<<"; backEdge: "<<t_isBackedge<<endl;
  list<CGRANode*> searchPool;
  map<CGRANode*, int> distance;
  map<CGRANode*, int> timing;
  map<CGRANode*, CGRANode*> previous;
  timing[t_srcCGRANode] = m_mappingTiming[t_srcDFGNode];
  // Check whether the II is violated on each cycle.
  if (t_srcDFGNode->shareSameCycle(t_dstDFGNode)) {
    list<list<DFGNode*>*>* dfgNodeCycles = t_dfg->getCycleLists();
    for (list<DFGNode*>* cycle: *dfgNodeCycles) {
      bool foundSrc = (find(cycle->begin(), cycle->end(), t_srcDFGNode) != cycle->end());
      bool foundDst = (find(cycle->begin(), cycle->end(), t_dstDFGNode) != cycle->end());
      if (!foundSrc or !foundDst) {
        continue;
      }
      int totalTime = 0;
      DFGNode* lastDFGNode = cycle->back();
      for (DFGNode* dfgNode: *cycle) {
        if (m_mappingTiming.find(dfgNode) == m_mappingTiming.end() or
            m_mappingTiming.find(lastDFGNode) == m_mappingTiming.end()) {
          totalTime = 0;
          break;
        } else {
          int t1 = m_mappingTiming[lastDFGNode];
          int t2 = m_mappingTiming[dfgNode];
          while (t1 >= t2) {
            t2 += t_II;
          }
          totalTime += t2 - t1;
        }
        lastDFGNode = dfgNode;
      }
      if (totalTime > t_II) {
        cout<<"[DEBUG] cannot route due to II is violated for backward cycle"<<endl;
        return false;
      }
    }
  }
  for (int i=0; i<t_cgra->getRows(); ++i) {
    for (int j=0; j<t_cgra->getColumns(); ++j) {
      CGRANode* node = t_cgra->nodes[i][j];
      distance[node] = m_maxMappingCycle;
      timing[node] = timing[t_srcCGRANode];
      timing[node] += t_srcDFGNode->getExecLatency(node->getDVFSLatencyMultiple()) - 1;
//      if (t_srcDFGNode->isLoad() or t_srcDFGNode->isStore()) {
//        timing[node] += 1;
//      }
      previous[node] = NULL;
      searchPool.push_back(t_cgra->nodes[i][j]);
    }
  }
  distance[t_srcCGRANode] = 0;
  while (searchPool.size()!=0) {
    int minCost = m_maxMappingCycle + 1;
    CGRANode* minNode;
    for (CGRANode* currentNode: searchPool) {
      if (distance[currentNode] < minCost) {
        minCost = distance[currentNode];
        minNode = currentNode;
      }
    }
    searchPool.remove(minNode);
    // found the target point in the shortest path
    if (minNode == t_dstCGRANode) {
      if (previous[minNode] == NULL)
        break;
    }
    list<CGRANode*>* currentNeighbors = minNode->getNeighbors();

    for (CGRANode* neighbor: *currentNeighbors) {
      int cycle = timing[minNode];
      while (1) {
        CGRALink* currentLink = minNode->getOutLink(neighbor);
        // TODO: should also consider the cost of the register file
        if (currentLink->canOccupy(t_srcDFGNode, t_srcCGRANode, cycle, t_II)) {
          // rough estimate the cost based on the suspend cycle
          int cost = distance[minNode] + (cycle - timing[minNode]) + 1;
          if (cost < distance[neighbor]) {
            distance[neighbor] = cost;
            timing[neighbor] = cycle + 1;
            previous[neighbor] = minNode;
          }
          break;
        }
        ++cycle;
        if(cycle > m_maxMappingCycle)
          break;
      }
    }
  }

  // Construct the shortest path for routing.
  map<CGRANode*, int> path;
  CGRANode* u = t_dstCGRANode;
  if (previous[u] != NULL or u == t_srcCGRANode) {
    while (u != NULL) {
      path[u] = timing[u];
      u = previous[u];
    }
  } else {
    cout<<"[DEBUG] cannot route due to a path cannot be constructed"<<endl;
    return false;
  }

  // Not a valid mapping if it exceeds the 'm_maxMappingCycle'.
  // I don't think we need check II here.
  if(timing[t_dstCGRANode] > m_maxMappingCycle) {
    // timing[t_dstCGRANode] - timing[t_srcCGRANode] > t_II) {
    // cout<<"[DEBUG] cannot route due to II violation case 2: timing[CGRANode "<<t_dstCGRANode->getID()<<"] "<<timing[t_dstCGRANode]<<" - timing[CGRANode "<<t_srcCGRANode->getID()<<"] "<<timing[t_srcCGRANode]<<" > II "<<t_II<<endl;
    return false;
  }


//  if (timing[t_dstCGRANode]%t_II >= t_dstCycle%t_II)
  // Try to route the data flow.
  map<int, CGRANode*>* reorderPath = getReorderPath(&path);
//  //Since the cycle on path increases gradually, re-order will not miss anything.
//  for(map<CGRANode*, int>::iterator iter=path.begin(); iter!=path.end(); ++iter) {
//    reorderPath[(*iter).second] = (*iter).first;
//  }
//  assert(reorderPath.size() == path.size());

  map<int, CGRANode*>::iterator previousIter;
  map<int, CGRANode*>::reverse_iterator riter = reorderPath->rbegin();
  cout<<"[DEBUG] check route size: "<<reorderPath->size()<<"\n";
  if (reorderPath->size() == 1) {
    int duration = (t_II+(t_dstCycle-(*riter).first)%t_II)%t_II;
    cout<<"[DEBUG] allocate for local reg maintain... duration="<<duration<<" last cycle: "<<(*riter).first<<"\n";
    (*riter).second->allocateReg(4, (*riter).first, duration, t_II);
  }
  bool generatedOut = true;
  for (map<int, CGRANode*>::iterator iter = reorderPath->begin();
      iter!=reorderPath->end(); ++iter) {
    if (iter != reorderPath->begin()) {
      CGRALink* l = t_cgra->getLink((*previousIter).second, (*iter).second);
      bool isBypass = false;
      int duration = ((*iter).first-(*previousIter).first)%t_II;
      if ((*riter).second != (*iter).second and
          (*previousIter).first+1 == (*iter).first)
        isBypass = true;
      else {
        duration = (t_II+(t_dstCycle-(*previousIter).first)%t_II)%t_II;
        cout<<"[DEBUG] reset duration: "<<duration<<" t_dstCycle: "<<t_dstCycle<<" previous: "<<(*previousIter).first<<" II: "<<t_II<<"\n";
      }
      if (duration == 0) {
        cout<<"[DEBUG] reset duration is 0...\n";
        // The successor can only be done within an interval of II, otherwise
        // the II is no longer II but II*2.
        if (t_isBackedge) {
          cout<<"[DEBUG] cannot route due to backedge"<<endl;
          return false;
        }
        duration = t_II;
      }
      l->occupy(t_srcDFGNode, (*previousIter).first,
                duration, t_II, isBypass, generatedOut, t_isStaticElasticCGRA);
      generatedOut = false;
    }
    previousIter = iter;
  }

  map<int, CGRANode*>::iterator begin = reorderPath->begin();
  map<int, CGRANode*>::reverse_iterator end = reorderPath->rbegin();

  // Check whether the backward data can be delivered within II.
  if (!t_isStaticElasticCGRA) {
    if (t_isBackedge and (*end).first - (*begin).first >= t_II) {
      cout<<"[DEBUG] cannot route due to backedge data cannot be delivered in time"<<endl;
      return false;
    }
  }
  return true;
}

int Mapper::heuristicMap(CGRA* t_cgra, DFG* t_dfg, int t_II,
    bool t_isStaticElasticCGRA) {
  bool fail = false;
  while (1) {
    cout<<"----------------------------------------\n";
    cout<<"[DEBUG] start heuristic algorithm with II="<<t_II<<"\n";
    int cycle = 0;
    constructMRRG(t_dfg, t_cgra, t_II);
    fail = false;
    for (list<DFGNode*>::iterator dfgNode=t_dfg->nodes.begin();
        dfgNode!=t_dfg->nodes.end(); ++dfgNode) {
      
      list<map<CGRANode*, int>*> paths;

      #pragma omp parallel
      {
          list<map<CGRANode*, int>*> paths_private;
          #pragma omp for collapse(2) nowait
          for (int i=0; i<t_cgra->getRows(); ++i) {
            for (int j=0; j<t_cgra->getColumns(); ++j) {
              CGRANode* fu = t_cgra->nodes[i][j];
              map<CGRANode*, int>* tempPath =
                  calculateCost(t_cgra, t_dfg, t_II, *dfgNode, fu);
              if(tempPath != NULL && tempPath->size() != 0) {
                paths_private.push_back(tempPath);
              }
            }
          }
          #pragma omp critical
          {
              paths.splice(paths.end(), paths_private);
          }
      }
      // Found some potential mappings.
      if (paths.size() != 0) {
        map<CGRANode*, int>* optimalPath =
            getPathWithMinCostAndConstraints(t_cgra, t_dfg, t_II, *dfgNode, &paths);
        if (optimalPath->size() != 0) {
          if (!schedule(t_cgra, t_dfg, t_II, *dfgNode, optimalPath,
              t_isStaticElasticCGRA)) {
            cout<<"[DEBUG] fail1 in schedule() II: "<<t_II<<"\n";
            for (map<CGRANode*,int>::iterator iter = optimalPath->begin();
                iter!=optimalPath->end(); ++iter) {
              cout<<"[DEBUG] the failed path -- cycle: "<<(*iter).second<<" CGRANode: "<<(*iter).first->getID()<<"\n";
            }

            fail = true;
            break;
          }
          cout<<"[DEBUG] success in schedule()\n";
        } else {
          cout<<"[DEBUG] fail2 in schedule() II: "<<t_II<<"\n";
          fail = true;
          break;
        }
      } else {
        fail = true;
        cout<<"[DEBUG] *else* no available path for DFG node "<<(*dfgNode)->getID()
            <<" within II "<<t_II<<".\n";
        break;
      }
    }
    if (!fail)
      break;
    else if (t_isStaticElasticCGRA) {
      break;
    }
    ++t_II;
  }
  if (!fail)
    return t_II;
  else
    return -1;
}

int Mapper::exhaustiveMap(CGRA* t_cgra, DFG* t_dfg, int t_II,
    bool t_isStaticElasticCGRA) {
  list<map<CGRANode*, int>*>* exhaustivePaths = new list<map<CGRANode*, int>*>();
  list<DFGNode*>* mappedDFGNodes = new list<DFGNode*>();
  bool success = DFSMap(t_cgra, t_dfg, t_II, mappedDFGNodes,
      exhaustivePaths, t_isStaticElasticCGRA);
  if (success)
    return t_II;
  else
    return -1;
}

bool Mapper::DFSMap(CGRA* t_cgra, DFG* t_dfg, int t_II,
    list<DFGNode*>* t_mappedDFGNodes,
    list<map<CGRANode*, int>*>* t_exhaustivePaths,
    bool t_isStaticElasticCGRA) {
//  , DFGNode* t_badMappedDFGNode) {

//  list<map<CGRANode*, int>*>* exhaustivePaths = t_exhaustivePaths;

  constructMRRG(t_dfg, t_cgra, t_II);

//  list<DFGNode*> dfgNodeSearchPool;
//  for (list<DFGNode*>::iterator dfgNodeItr=dfg->nodes.begin();
//      dfgNodeItr!=dfg->nodes.end(); ++dfgNodeItr) {
//    dfgNodeSearchPool.push_back(*dfgNodeItr);
//  }

  list<DFGNode*>::iterator mappedDFGNodeItr = t_mappedDFGNodes->begin();
  list<DFGNode*>::iterator dfgNodeItr = t_dfg->nodes.begin();
//  list<DFGNode*>::iterator dfgNodeItr = t_dfg->getDFSOrderedNodes()->begin();
  for (map<CGRANode*, int>* path: *t_exhaustivePaths) {
    if (!schedule(t_cgra, t_dfg, t_II, *mappedDFGNodeItr, path,
        t_isStaticElasticCGRA)) {
      cout<<"DEBUG <this is impossible> fail3 in DFS() II: "<<t_II<<"\n";
      assert(0);
      break;
    }
    ++mappedDFGNodeItr;
//    dfgNodeSearchPool.remove(*dfgNodeItr);
    ++dfgNodeItr;
  }
//  if (dfgNodeSearchPool.size() == 0) {
  if (dfgNodeItr == t_dfg->nodes.end())
    return true;
//  }

  DFGNode* targetDFGNode = *dfgNodeItr;

  list<map<CGRANode*, int>*> paths;
  for (int i=0; i<t_cgra->getRows(); ++i) {
    for (int j=0; j<t_cgra->getColumns(); ++j) {
      CGRANode* fu = t_cgra->nodes[i][j];
      map<CGRANode*, int>* tempPath =
          calculateCost(t_cgra, t_dfg, t_II, targetDFGNode, fu);
      if(tempPath != NULL and tempPath->size() != 0) {
        paths.push_back(tempPath);
      }
    }
  }

  list<map<CGRANode*, int>*>* potentialPaths =
      getOrderedPotentialPaths(t_cgra, t_dfg, t_II, targetDFGNode, &paths);
  bool success = false;
  while (potentialPaths->size() != 0) {
    map<CGRANode*, int>* currentPath = potentialPaths->front();
    potentialPaths->pop_front();
    assert(currentPath->size() != 0);
    if (schedule(t_cgra, t_dfg, t_II, targetDFGNode, currentPath,
        t_isStaticElasticCGRA)) {
      t_exhaustivePaths->push_back(currentPath);
      t_mappedDFGNodes->push_back(targetDFGNode);
      success = DFSMap(t_cgra, t_dfg, t_II, t_mappedDFGNodes,
          t_exhaustivePaths, t_isStaticElasticCGRA);
      if (success)
        return true;
    }
    // If the schedule fails and need to try the other schedule,
    // should re-construct m_mapping and m_mappingTiming.
    constructMRRG(t_dfg, t_cgra, t_II);
    list<DFGNode*>::iterator mappedDFGNodeItr = t_mappedDFGNodes->begin();
    for (map<CGRANode*, int>* path: *t_exhaustivePaths) {
      if (!schedule(t_cgra, t_dfg, t_II, *mappedDFGNodeItr, path,
          t_isStaticElasticCGRA)) {
        cout<<"DEBUG <this is impossible> fail7 in DFS() II: "<<t_II<<"\n";
        assert(0);
        break;
      }
      ++mappedDFGNodeItr;
    }
  }
  if (t_exhaustivePaths->size() != 0) {
    cout<<"======= go backward one step ======== popped DFG node ["<<t_mappedDFGNodes->back()->getID()<<"] from CGRA node ["<<m_mapping[t_mappedDFGNodes->back()]->getID()<<"]\n";
    t_mappedDFGNodes->pop_back();
    t_exhaustivePaths->pop_back();
//    m_exit++;
//    if (m_exit == 2)
//      exit(0);
  }
  delete potentialPaths;
  return false;
}

// This helper function assume the cycle for each mapped CGRANode increases
// gradually along the path. Otherwise, the map struct will get conflict key.
map<int, CGRANode*>* Mapper::getReorderPath(map<CGRANode*, int>* t_path) {
  map<int, CGRANode*>* reorderPath = new map<int, CGRANode*>();
  for (map<CGRANode*, int>::iterator iter=t_path->begin();
      iter!=t_path->end(); ++iter) {
    assert(reorderPath->find((*iter).second) == reorderPath->end());
    (*reorderPath)[(*iter).second] = (*iter).first;
  }
  assert(reorderPath->size() == t_path->size());
  return reorderPath;
}

// Saves the mapping results to json file for subsequent incremental mapping.
void Mapper::generateJSON4IncrementalMap(CGRA* t_cgra, DFG* t_dfg){
  ofstream jsonFile("increMapInput.json", ios::out);
  jsonFile<<"{"<<endl;
  jsonFile<<"     \"Opt2TileXY\":{"<<endl;
  int idx = 0;
  for (DFGNode* dfgNode: t_dfg->nodes) {
    // Writes dfgnodeID, mapped CGRANode X and Y coordinates.i
    // opt id.
    jsonFile<<"             \""<<dfgNode->getID()<<"\": {"<<endl;
    // opt mapped tile x coordinate.
    jsonFile<<"                     \"x\":"<<m_mapping[dfgNode]->getX()<<","<<endl;
    // opt mapped tile y coordinate.
    jsonFile<<"                     \"y\":"<<m_mapping[dfgNode]->getY()<<endl;
    idx += 1;
    if (idx < t_dfg->nodes.size()) jsonFile<<"             },"<<endl;
    else jsonFile<<"        }"<<endl;
  }
  jsonFile<<"     },"<<endl;

  jsonFile<<"     \"Tile2Level\":{"<<endl;
  // Generates level informations of current mapping results.
  // FanIO is the number of links of current CGRANode connected to other CGRANode,
  // and FanIO_CGRANodes can help with querying the list of CGRANodes with the given FanIO.
  vector<int> FanIOs;
  map<int, vector<CGRANode*>> FanIO_CGRANodes;
  int numTiles = 0;
  for (int i=0; i<t_cgra->getRows(); ++i) {
    for (int j=0; j<t_cgra->getColumns(); ++j) {

      // Records the number of FanIO for each tile.
      CGRANode* currentCGRANode = t_cgra->nodes[i][j];
      // Only records tiles that have DFGNodes mapped.
      if (currentCGRANode->getInLinks() == 0) continue;
      int FanIO = max(currentCGRANode->getInLinks()->size(), currentCGRANode->getOutLinks()->size());
      FanIO_CGRANodes[FanIO].push_back(currentCGRANode);

      // Records FanIO in the list if it appears for the first time.
      if (find(FanIOs.begin(), FanIOs.end(), FanIO) == FanIOs.end()) {
        FanIOs.push_back(FanIO);
      }

      numTiles++;
    }
  }

  // Sorts FanIOs from big to small helps automatically form the level.
  // Level indicates the ranking of CGRA according to the FanIOs that CGRANode has,
  // high level means higher FanIOs, CGRANodes within the same level have same FanIOs.
  std::sort(FanIOs.rbegin(), FanIOs.rend());
  idx = 0;
  for (int level = 0; level < FanIOs.size(); level++) {
    int FanIO = FanIOs[level];
    vector<CGRANode*> tiles = FanIO_CGRANodes[FanIO];
    for (auto tile : tiles) {
      idx += 1;
      if (idx < numTiles) jsonFile<<"          \""<<tile->getID()<<"\":"<<level<<","<<endl;
      else jsonFile<<"             \""<<tile->getID()<<"\":"<<level<<endl;
    }
  }
  jsonFile<<"     }"<<endl;

  jsonFile<<"}"<<endl;
  jsonFile.close();
}

// Reads from the referenced mapping results json file and generates variables for incremental mapping.
int Mapper::readRefMapRes(CGRA* t_cgra, DFG* t_dfg){
  ifstream refFile("./increMapInput.json");
  if (!refFile.good()) {
    cout<<"Incremental mapping requires increMapInput.json in current directory!"<<endl;
    return -1;
  }
  json refs;
  refFile >> refs;
  CGRANodeID2Level.clear();
  for (list<DFGNode*>::iterator dfgNode=t_dfg->nodes.begin(); dfgNode != t_dfg->nodes.end(); ++dfgNode) {
    int dfgNodeID = (*dfgNode)->getID();
    int x = refs["Opt2TileXY"][to_string(dfgNodeID)]["x"];
    int y = refs["Opt2TileXY"][to_string(dfgNodeID)]["y"];
    refMapRes[*dfgNode] = t_cgra->nodes[y][x];
    int cgraNodeID = t_cgra->nodes[y][x]->getID();
    CGRANodeID2Level[cgraNodeID] = refs["Tile2Level"][to_string(cgraNodeID)];
  }

  return 0;
}

// Generates variables for incremental mapping.
void Mapper::sortAllocTilesByLevel(CGRA* t_cgra){
  map<int, vector<CGRANode*>> FanIO_CGRANodes;
  vector<int> FanIOs;
  int numTiles = 0;
  for (int i=0; i<t_cgra->getRows(); ++i) {
    for (int j=0; j<t_cgra->getColumns(); ++j) {

      // Records the number of FanIO for each tile.
      CGRANode* currentCGRANode = t_cgra->nodes[i][j];
      // only record tiles that have DFGNodes mapped.
      if (currentCGRANode->isDisabled()) continue;
      int FanIO = max(currentCGRANode->getInLinks()->size(), currentCGRANode->getOutLinks()->size());
      FanIO_CGRANodes[FanIO].push_back(currentCGRANode);

      // Records FanIO in the list if it appears for the first time.
      if (find(FanIOs.begin(), FanIOs.end(), FanIO) == FanIOs.end()) {
        FanIOs.push_back(FanIO);
      }

      numTiles++;
    }
  }
  // Sorts FanIOs from big to small to automatically form the level.
  std::sort(FanIOs.rbegin(), FanIOs.rend());

  CGRANodes_sortedByLevel.clear();
  for (int level = 0; level < FanIOs.size(); level++) {
    int FanIO = FanIOs[level];
    vector<CGRANode*> tiles = FanIO_CGRANodes[FanIO];
    CGRANodes_sortedByLevel.push_back(tiles);
  }
}

// Generates the placement recommendation list for current DFGNode
// by referencing its placement in the former mapping results.
// Two principles: Reference Placement Tendency (RPT) & Minimize Bypass Operations (MBO).
list<CGRANode*> Mapper::placementGen(CGRA* t_cgra,  DFGNode* t_dfgNode){
  list<CGRANode*> placementRecommList;
  CGRANode* refCGRANode = refMapRes[t_dfgNode];
  list<DFGNode*>* predNodes = t_dfgNode->getPredNodes();
  // The level is used to ordering the CGRANodes based on the FanIO.
  // Though FanIO of each CGRANode would change for different CGRA architectures,
  // the DFGNode prefers to being mapped onto the CGRANode with same level.
  int refLevel = CGRANodeID2Level[refCGRANode->getID()];
  int level = refLevel;
  int maxLevel = CGRANodes_sortedByLevel.size() - 1;
  cout<<t_dfgNode->getOpcodeName()<<t_dfgNode->getID()<<" is mapped to Tile "<<refCGRANode->getID()<<" in the referenced mapping results, refLevel="<<refLevel<<endl;

  int initLevel = level;
  while (true) {
    // Sorts the CGRANodes with the number of bypass operations
    // required to communicate with its predecessors.
    map<int, vector<CGRANode*>> bypassNums_CGRANode;
    int curX, curY, preX, preY;
    int xdiff, ydiff;
    for (auto curCGRANode : CGRANodes_sortedByLevel[level]) {
      int numBypass = 0;
      for (DFGNode* pre: *predNodes) {
        if (m_mapping.find(pre) != m_mapping.end()) {
          CGRANode* preCGRANode = m_mapping[pre];
          xdiff = abs(curCGRANode->getX() - preCGRANode->getX());
          ydiff = abs(curCGRANode->getY() - preCGRANode->getY());
          numBypass += (xdiff + ydiff);
        }
        else continue;
      }
      bypassNums_CGRANode[numBypass].push_back(curCGRANode);
    }

    // bypassNums_CGRANode is sorted by key from smallest to largest by default,
    // and tile with fewer bypass nodes has higher priority.
    for (auto iter : bypassNums_CGRANode) {
      for (auto tile : iter.second) {
        placementRecommList.push_back(tile);
      }
    }

    level += 1;
    if (level > maxLevel) {
      // Goes back to the highest level.
      level = 0;
    }
    if (level == initLevel) break;
  }

  return placementRecommList;
}

// Incremental mapping function.
int Mapper::incrementalMap(CGRA* t_cgra, DFG* t_dfg, int t_II){
  if (readRefMapRes(t_cgra, t_dfg) == -1) return -1;
  sortAllocTilesByLevel(t_cgra);

  bool dfgNodeMapFailed;
  while (1) {
    cout<<"----------------------------------------\n";
    cout<<"[DEBUG] start incremental mapping  with II="<<t_II<<"\n";
    int cycle = 0;
    constructMRRG(t_dfg, t_cgra, t_II);
    for (list<DFGNode*>::iterator dfgNode=t_dfg->nodes.begin(); dfgNode!=t_dfg->nodes.end(); dfgNode++) {
      list<CGRANode*> placementRecommList = placementGen(t_cgra, *dfgNode);
      dfgNodeMapFailed = true;
      for (auto fu : placementRecommList) {
        map<CGRANode*, int>* path = calculateCost(t_cgra, t_dfg, t_II, *dfgNode, fu);
        if (path == NULL) {
          // Switches to the next tile.
          cout<<"[DEBUG] no available path for DFG node "<<(*dfgNode)->getID()<<" on CGRA node "<<fu->getID()<<" within II "<<t_II<<endl;
          continue;
        }
        else {
          if (schedule(t_cgra, t_dfg, t_II, *dfgNode, path, false)) {
            // Current DFGNode is scheduled successfully, moves to the next DFGNode.
            dfgNodeMapFailed = false;
            break;
          }
          else {
            // Switches to the next tile.
            cout<<"[DEBUG] no available path to schedule DFG node "<<(*dfgNode)->getID()<<" on CGRA node "<<fu->getID()<<" within II "<<t_II<<endl;
            continue;
          }
        }
      }
      // Increases II and restart if current DFGNode fails the mapping.
      if (dfgNodeMapFailed) break;
    }

    if (dfgNodeMapFailed) {
      cout<<"[DEBUG] fail in schedule() under II: "<<t_II<<"\n";
      t_II++;
    }
    else {
      cout<<"[DEBUG] success in schedule() under II: "<<t_II<<"\n";
      return t_II;
    }
  }

  return -1;
}

