/*
 * ======================================================================
 * CGRA.cpp
 * ======================================================================
 * CGRA implementation.
 *
 * Author : Cheng Tan
 *   Date : Jan 9, 2023
 */

#include <fstream>
#include "CGRA.h"
#include "json.hpp"

using json = nlohmann::json;

CGRA::CGRA(int t_rows, int t_columns, std::string t_vectorizationMode,
	   list<string>* t_fusionStrategy, bool t_parameterizableCGRA,
	   map<string, list<int>*>* t_additionalFunc,
	   bool t_supportDVFS, int t_DVFSIslandDim, bool enableMultipleOps) {
  m_rows = t_rows;
  m_columns = t_columns;
  m_FUCount = t_rows * t_columns;
  m_supportDVFS = t_supportDVFS;
  m_DVFSIslandDim = t_DVFSIslandDim;
  m_supportInclusive = enableMultipleOps;
  m_supportComplex = new list<string>();
  m_supportCall = new list<string>();
  nodes = new CGRANode**[t_rows];

  // Initialize the m_supportComplex & m_supportCall list.
  for (auto x: *t_additionalFunc) {
    string func = x.first;
    if (func.find("call") != string::npos) {
      if (func.length() == 4) {
        m_supportCall->push_back("");
      } else {
        m_supportCall->push_back(func.substr(func.find("call") + 5));
      }
    } else if (func.find("complex") != string::npos) {
      if (func.length() == 7) {
        m_supportComplex->push_back("");
      } else {
        m_supportComplex->push_back(func.substr(func.find("complex") + 8));
      }
    }
  }

  if (t_parameterizableCGRA) {

    int node_id = 0;
    map<int, CGRANode*> id2Node;
    for (int i=0; i<t_rows; ++i) {
      nodes[i] = new CGRANode*[t_columns];
      for (int j=0; j<t_columns; ++j) {
        nodes[i][j] = new CGRANode(node_id, j, i);
        if (!enableMultipleOps) {
          nodes[i][j]->disableMultipleOps();
        }
	// nodes[i][j]->disableAllFUs();
	id2Node[node_id] = nodes[i][j];
	node_id += 1;
      }
    }

    ifstream paramCGRA("./param.json");
    if (!paramCGRA.good()) {
      cout<<"Parameterizable CGRA design/mapping requires paramCGRA.json"<<endl;
      return;
    }
    json param;
    paramCGRA >> param;

    int numOfNodes = t_rows * t_columns;
    for (int nodeID = 0; nodeID < numOfNodes; ++nodeID) {
      bool disabled = param["tiles"][to_string(nodeID)]["disabled"];
      if (disabled) {
        id2Node[nodeID]->disable();
      } else {
        bool supportAllFUs = param["tiles"][to_string(nodeID)]["supportAllFUs"];
        if (supportAllFUs) {
          // Enables all FUs.
          id2Node[nodeID]->enableAdd();
          id2Node[nodeID]->enableBr();
          id2Node[nodeID]->enableCmp();
          id2Node[nodeID]->enableLoad();
          id2Node[nodeID]->enableLogic();
          id2Node[nodeID]->enableMAC();
          id2Node[nodeID]->enableMul();
          id2Node[nodeID]->enablePhi();
          id2Node[nodeID]->enableReturn();
          id2Node[nodeID]->enableSel();
          id2Node[nodeID]->enableShift();
          id2Node[nodeID]->enableStore();
        } else {
          id2Node[nodeID]->disableAllFUs();
          auto supportedFUs = param["tiles"][to_string(nodeID)]["supportedFUs"];
          cout << "Node " << nodeID << " supports: ";
          for (const auto& fu : supportedFUs) {
            cout << fu << " ";
            if (fu == "Add") {
              id2Node[nodeID]->enableAdd();
            } else if (fu == "Br") {
              id2Node[nodeID]->enableBr();
            } else if (fu == "Cmp") {
              id2Node[nodeID]->enableCmp();
            } else if (fu == "Ld") {
              id2Node[nodeID]->enableLoad();
            } else if (fu == "Logic") {
              id2Node[nodeID]->enableLogic();
            } else if (fu == "MAC") {
              id2Node[nodeID]->enableMAC();
            } else if (fu == "Mul") {
              id2Node[nodeID]->enableMul();
            } else if (fu == "Phi") {
              id2Node[nodeID]->enablePhi();
            } else if (fu == "Ret") {
              id2Node[nodeID]->enableReturn();
            } else if (fu == "Sel") {
              id2Node[nodeID]->enableSel();
            } else if (fu == "Shift") {
              id2Node[nodeID]->enableShift();
            } else if (fu == "St") {
              id2Node[nodeID]->enableStore();
            }
          }
          cout << " \n " << endl;
        }
	if (param["tiles"][to_string(nodeID)].contains("accessMem")) {
	  if (param["tiles"][to_string(nodeID)]["accessMem"]) {
	    id2Node[nodeID]->enableLoad();
	    id2Node[nodeID]->enableStore();
	  }
	}
      }
    }

    json paramLinks = param["links"];
    m_LinkCount = paramLinks.size();
    links = new CGRALink*[m_LinkCount];

    for (int linkID = 0; linkID < paramLinks.size(); ++linkID) {
      int srcNodeID = paramLinks[linkID]["srcTile"];
      int dstNodeID = paramLinks[linkID]["dstTile"];

      links[linkID] = new CGRALink(linkID);
      id2Node[srcNodeID]->attachOutLink(links[linkID]);
      id2Node[dstNodeID]->attachInLink(links[linkID]);
      links[linkID]->connect(id2Node[srcNodeID], id2Node[dstNodeID]);
    }

    // need to perform disable() again, as it will disable the related links
    for (int nodeID = 0; nodeID < numOfNodes; ++nodeID) {
      bool disabled = param["tiles"][to_string(nodeID)]["disabled"];
      if (disabled) {
        id2Node[nodeID]->disable();
      }
    }

  } else {

    int node_id = 0;
    for (int i=0; i<t_rows; ++i) {
      nodes[i] = new CGRANode*[t_columns];
      for (int j=0; j<t_columns; ++j) {
        nodes[i][j] = new CGRANode(node_id++, j, i);
        if (!enableMultipleOps) {
          nodes[i][j]->disableMultipleOps();
        }
      }
    }

    m_LinkCount = 2 * (t_rows * (t_columns-1) + (t_rows-1) * t_columns);
    links = new CGRALink*[m_LinkCount];

    // Enable the load/store on specific CGRA nodes based on param.json.
    int loadCount = 0;
    int storeCount = 0;
    for (map<string, list<int>*>::iterator iter=t_additionalFunc->begin();
        iter!=t_additionalFunc->end(); ++iter) {
      for (int nodeIndex: *(iter->second)) {
        if (nodeIndex >= m_FUCount) {
          cout<<"\033[0;31mInvalid CGRA node ID "<<nodeIndex<<" for operation "<<iter->first<<"\033[0m"<<endl;
          continue;
        } else {
          int row = nodeIndex / m_columns;
          int col = nodeIndex % m_columns;
          bool canEnable = nodes[row][col]->enableFunctionality(iter->first);
          if (!canEnable) {
            cout<<"\033[0;31mInvalid operation "<<iter->first<<" on CGRA node ID "<<nodeIndex<<"\033[0m"<<endl;
          } else {
            if ((iter->first).compare("store") == 0) {
              storeCount += 1;
            }
            if ((iter->first).compare("load") == 0) {
              loadCount += 1;
            }
          }
        }
      }
    }
    if (storeCount == 0) {
      cout<<"Without customization in param.json, we enable store functionality on the left most column."<<endl;
      for (int r=0; r<t_rows; ++r) {
        nodes[r][0]->enableStore();
      }
    }
    if (loadCount == 0) {
      cout<<"Without customization in param.json, we enable load functionality on the left most column."<<endl;
      for (int r=0; r<t_rows; ++r) {
        nodes[r][0]->enableLoad();
      }
    }


    // Some other basic operations that can be indicated in the param.json:
    // Enable the specialized 'call' functionality.
    // for (int r=0; r<t_rows; ++r) {
    //   for (int c=0; c<t_columns; ++c) {
    //     nodes[r][c]->enableCall();
    //   }
    // }

    // Enable the vectorization.
    if (t_vectorizationMode == "interleaved") {
      for (int r=0; r<t_rows; ++r) {
        for (int c=0; c<t_columns; ++c) {
          if((r+c)%2 == 0)
            nodes[r][c]->enableVectorization();
        }
      }
    } else if (t_vectorizationMode == "all") {
      for (int r=0; r<t_rows; ++r) {
        for (int c=0; c<t_columns; ++c) {
          nodes[r][c]->enableVectorization();
        }
      }
    } else {
      // "none" or else will be treated as none.
      cout<<"No vectorization is enabled on the CGRA nodes."<<endl;
    }

    // Enable the heterogeneity.
    // if (t_fusionStrategy) {
    //   for (int r=0; r<t_rows; ++r) {
    //     for (int c=0; c<t_columns; ++c) {
    //       // if(c == 0 || (r%2==1 and c%2 == 1))
    //         nodes[r][c]->enableComplex();
    //     }
    //   }
    // }

    for (int r=0; r<t_rows; ++r) {
      for (int c=0; c<t_columns; ++c) {
        nodes[r][c]->enableReturn();
      }
    }

    // Connect the CGRA nodes with links.
    int link_id = 0;
    for (int i=0; i<t_rows; ++i) {
      for (int j=0; j<t_columns; ++j) {
        if (i < t_rows - 1) {
          links[link_id] = new CGRALink(link_id);
          nodes[i][j]->attachOutLink(links[link_id]);
          nodes[i+1][j]->attachInLink(links[link_id]);
          links[link_id]->connect(nodes[i][j], nodes[i+1][j]);
          ++link_id;
        }
        if (i > 0) {
          links[link_id] = new CGRALink(link_id);
          nodes[i][j]->attachOutLink(links[link_id]);
          nodes[i-1][j]->attachInLink(links[link_id]);
          links[link_id]->connect(nodes[i][j], nodes[i-1][j]);
          ++link_id;
        }
        if (j < t_columns - 1) {
          links[link_id] = new CGRALink(link_id);
          nodes[i][j]->attachOutLink(links[link_id]);
          nodes[i][j+1]->attachInLink(links[link_id]);
          links[link_id]->connect(nodes[i][j], nodes[i][j+1]);
          ++link_id;
        }
        if (j > 0) {
          links[link_id] = new CGRALink(link_id);
          nodes[i][j]->attachOutLink(links[link_id]);
          nodes[i][j-1]->attachInLink(links[link_id]);
          links[link_id]->connect(nodes[i][j], nodes[i][j-1]);
          ++link_id;
        }
      }
    }

    disableSpecificConnections();
  }

  if (t_supportDVFS) {
    for (int r=0; r<t_rows; ++r) {
      for (int c=0; c<t_columns; ++c) {
        nodes[r][c]->enableDVFS();
	int DVFSIslandX = c / t_DVFSIslandDim;
	int DVFSIslandY = r / t_DVFSIslandDim;
	int DVFSIslandId = DVFSIslandX + DVFSIslandY * t_columns / t_DVFSIslandDim;
        nodes[r][c]->setDVFSIsland(DVFSIslandX, DVFSIslandY, DVFSIslandId);
	// Islandize the CGRA nodes. In the prototype, each set of 2x2 nodes are
        // grouped as one island. For example, a 4x4 CGRA has 2x2 islands, the
        // tiles of (0, 2), (0, 3), (1, 2), (1, 3) are viewd as the (0, 1) island.
	if (m_DVFSIslands.find(DVFSIslandId) != m_DVFSIslands.end()) {
          m_DVFSIslands[DVFSIslandId].push_back(nodes[r][c]);
	} else {
          vector<CGRANode*> tiles{nodes[r][c]};
          m_DVFSIslands[DVFSIslandId] = tiles;
	}
      }
    }
  }

/*
  cout<<"[connection] horizontal and vertical."<<endl;
  // Connect the CGRA nodes with diagonal links.
  for (int i=0; i<t_rows-1; ++i) {
    for (int j=0; j<t_columns-1; ++j) {
      link = new CGRALink();
      nodes[i][j]->attachOutLink(link, _RIGHT_UP);
      nodes[i+1][j+1]->attachInLink(link, _LEFT_DOWN);
      link->connect(nodes[i][j], nodes[i+1][j+1]);
      m_links.push_back(link);

      link = new CGRALink();
      nodes[i+1][j+1]->attachOutLink(link, _LEFT_DOWN);
      nodes[i][j]->attachInLink(link, _RIGHT_UP);
      link->connect(nodes[i+1][j+1], nodes[i][j]);
      m_links.push_back(link);

      link = new CGRALink();
      nodes[i][j+1]->attachOutLink(link, _RIGHT_DOWN);
      nodes[i+1][j]->attachInLink(link, _LEFT_UP);
      link->connect(nodes[i][j+1], nodes[i+1][j]);
      m_links.push_back(link);

      link = new CGRALink();
      nodes[i+1][j]->attachOutLink(link, _LEFT_UP);
      nodes[i][j+1]->attachInLink(link, _RIGHT_DOWN);
      link->connect(nodes[i+1][j], nodes[i][j+1]);
      m_links.push_back(link);
    }
  }
  cout<<"[connection] diagonal."<<endl;
*/

}

list<string>* CGRA::getSupportComplex() {
    return m_supportComplex;
}

list<string>* CGRA::getSupportCall() {
    return m_supportCall;
}

void CGRA::disableSpecificConnections() {
//  nodes[0][0]->disable();
//  nodes[0][1]->disable();
//  nodes[0][2]->disable();
//  nodes[0][3]->disable();
//  nodes[0][4]->disable();
//  nodes[1][0]->disable();
//  nodes[1][1]->disable();
//  nodes[1][2]->disable();
//  nodes[1][4]->disable();
//  nodes[1][3]->disable();
//  nodes[2][0]->disable();
//  nodes[2][1]->disable();
//  nodes[2][2]->disable();
//  nodes[2][3]->disable();
//  nodes[2][4]->disable();
//  nodes[3][1]->disable();
//  nodes[3][2]->disable();
//  nodes[3][2]->disable();
//  nodes[3][3]->disable();
//  nodes[3][4]->disable();
//  nodes[4][1]->disable();
//  nodes[4][2]->disable();
//  nodes[4][3]->disable();
//  nodes[4][4]->disable();

}

void CGRA::setRegConstraint(int t_regConstraint) {
  for (int i=0; i<m_rows; ++i)
    for (int j=0; j<m_columns; ++j)
      nodes[i][j]->setRegConstraint(t_regConstraint);
}

void CGRA::setBypassConstraint(int t_bypassConstraint) {
  for (int i=0; i<m_LinkCount; ++i)
    links[i]->setBypassConstraint(t_bypassConstraint);
}

void CGRA::setCtrlMemConstraint(int t_ctrlMemConstraint) {
  for (int i=0; i<m_rows; ++i)
    for (int j=0; j<m_columns; ++j)
      nodes[i][j]->setCtrlMemConstraint(t_ctrlMemConstraint);

  for (int i=0; i<m_LinkCount; ++i)
    links[i]->setCtrlMemConstraint(t_ctrlMemConstraint);
}

int CGRA::getFUCount() {
  return m_FUCount;
}

void CGRA::constructMRRG(int t_II) {
  for (int i=0; i<m_rows; ++i)
    for (int j=0; j<m_columns; ++j)
      nodes[i][j]->constructMRRG(m_FUCount, t_II);
  for (int i=0; i<m_LinkCount; ++i)
    links[i]->constructMRRG(m_FUCount, t_II);
}

CGRALink* CGRA::getLink(CGRANode* t_n1, CGRANode* t_n2) {
   for (int i=0; i<m_LinkCount; ++i) {
     if (links[i]->getSrc()==t_n1 and links[i]->getDst() == t_n2) {
       return links[i];
     }
  }

  // cout << "bad query for CGRA link\n";
  return NULL;
}

int CGRA::getLinkCount() {
  return m_LinkCount;
}

map<int, vector<CGRANode*>> CGRA::getDVFSIslands() {
  return m_DVFSIslands;
}

void CGRA::syncDVFSIsland(CGRANode* t_node) {
  int islandID = t_node->getDVFSIslandID();
  for (auto& nodeWithinIsland : m_DVFSIslands[islandID]) {
    nodeWithinIsland->setDVFSLatencyMultiple(t_node->getDVFSLatencyMultiple());
    nodeWithinIsland->syncDVFS();
    cout << "[cheng] synced for node: " << nodeWithinIsland->getID() << "; check synced: " << nodeWithinIsland->isSynced() << "; addr: " << nodeWithinIsland << endl;
  }
}

bool CGRA::getSupportInclusive() {
  return m_supportInclusive;
}
