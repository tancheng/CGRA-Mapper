# Strcture
tools/
└── expandable/
    ├── README.md
    ├── __init__.py
    ├── main.py
    ├── scheduler.py
    └── visualization.py
    ├── fig/
    ├── result/
    ├── tmp/

# Explain
- main.py generates simulated real-world tasks and model the corresponding Neura execution progress on different multi-CGRA designs.
- scheduler.py recieves tasks and generates corresponding kernel mapping infomation in /tmp/. The output of it is in /result/, that is the execution information recorded during the progress.
- visulization.py reads the /result/ csv document and generates figs in our Neura paper.