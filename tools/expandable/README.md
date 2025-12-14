# Strcture
tools/
└── expandable/
    ├── README.md              # This file
    ├── __init__.py
    ├── main.py                # Neura demo script
    ├── designs/               # input json for Neura Scalibility evaluation
    │   ├── 2x2baseline.json
    │   ├── 2x2task.json
    │   ├── 3x3task.json
    │   ├── 4x4task.json
    │   └── 5x5task.json
    ├── util/                  # Utility modules
    │   ├── __init__.py
    │   ├── scheduler.py      # Kernel mapping and task scheduling
    │   └── visualizer.py     # Result visualization
    ├── fig/                  # Generated figures
    ├── result/               # Scheduling results
    └── tmp/                  # Kernel mapping results

# Core components
- main.py generates simulated real-world tasks and models the execution progress across different evaluation settings.
- scheduler.py recieves tasks and generates kernel mapping information (stored in /tmp/). It also outputs scheduling results to /result/ directory.
- visulization.py reads csv from /result/ and generates paper figures in /figs/ directory.

# Outputs
- /fig/Fig9.png: Normalized execution time and improved utilization
- /fig/Fig10.png: Normalized throughput speedup
- /fig/Fig11.png: Scalability -- Normalized execution time and improved utilization