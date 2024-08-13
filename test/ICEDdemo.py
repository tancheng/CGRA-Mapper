# ----------------------------------------------------------------------------
#   Filename: testT3forDVFS.py                                              /
#   Description: script of ICED                                       /
#   Author: Miaomiao Jiang, strat from 2023-10-16                           /
# ----------------------------------------------------------------------------

import os
import subprocess
import json
import time        
import eventlet    # for time out
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ----------------------------------------------------------------------------
#   global variables in testT3forDVFS.py                                    /
# ----------------------------------------------------------------------------

testBenchs = ["fir.cpp", "latnrm.c", "fft.c", "dtw.cpp", "spmv.c", "conv.c", "relu.c", "histogram.cpp", "mvt.c", "gemm.c", 
"aggregate1.c", "aggregate2.c", "combine.c", "combineRelu.c", "compress.cpp", "pooling.c", "decompose.cpp", 
"init.cpp", "invert.cpp", "solver0.cpp"] # the file type of kernels must match
testBenchsNum = len(testBenchs)
dictCvs = {'kernels': "", 'DFG nodes': "", 'DFG edges': "", 'recMII': "", 'avg tile utilization': "", '0% tiles u': "", 'avg tile frequency': "",	'0% tiles f': "", 
'25% tiles f': "",'50% tiles f': "", '100% tiles f': ""}  # column names of generated CVS
dictColumn = len(dictCvs)
jsonName = "./paramDVFS.json"   # name of generated json file
timeOutSet = 180   # set Timeout = 3 minutes
# for showTable(), showFig9(), showFig10(), showFig11() since they all read the 6x6_*_*.csv
fileBaselineU1 = "./tmp/t_6x6_unroll1_baseline.csv"  
fileBaselineU2 = "./tmp/t_6x6_unroll2_baseline.csv"   
filePertileU1 = "./tmp/t_6x6_unroll1_pertile.csv"
filePertileU2 = "./tmp/t_6x6_unroll2_pertile.csv"  
fileIcedU1 = "./tmp/t_6x6_unroll1_iced.csv"
fileIcedU2 = "./tmp/t_6x6_unroll2_iced.csv"

# For your convience, the names of cvs are listed to avoid wating for the cvs generation in main function.
# nameCvsBaseline = ["./tmp/t_2x2_unroll1_baseline.csv", "./tmp/t_4x4_unroll1_baseline.csv", "./tmp/t_6x6_unroll1_baseline.csv", 
# "./tmp/t_6x6_unroll2_baseline.csv", "./tmp/t_8x8_unroll1_baseline.csv", "./tmp/t_8x8_unroll2_baseline.csv"]
# nameCvsPertile = ["./tmp/t_2x2_unroll1_pertile.csv", "./tmp/t_4x4_unroll1_pertile.csv", "./tmp/t_6x6_unroll1_pertile.csv", 
# "./tmp/t_6x6_unroll2_pertile.csv", "./tmp/t_8x8_unroll1_pertile.csv", "./tmp/t_8x8_unroll2_pertile.csv"]
# nameCvsIced = ["./tmp/t_2x2_unroll1_iced.csv", "./tmp/t_4x4_unroll1_iced.csv","./tmp/t_6x6_unroll1_iced.csv", 
# "./tmp/t_6x6_unroll2_iced.csv", "./tmp/t_8x8_unroll1_iced.csv", "./tmp/t_8x8_unroll2_iced.csv"] 

# ----------------------------------------------------------------------------
#   function defination in testT3forDVFS.py                                 /
# ----------------------------------------------------------------------------

def DVFSComp(fileName, uFactor):
    """
    This is a func compile kernels using clang with selected unrolling factor.

    Parameters: kernel name, unrolling factor

    Returns: function name of given kernel 
    """
    fileSource = (fileName.split("."))[0]

    uCommand0 = "clang-12 -emit-llvm -fno-unroll-loops -O3 -o kernel.bc -c "    # no unroll
    uCommand2 = "clang-12 -emit-llvm -funroll-loops -mllvm -unroll-count=2 -O3 -o kernel.bc -c "    # unroll = 2
    appCommand0 = "./kernels/"
    generalCommand = fileSource + "/" + fileName
    compileCommand = ""

    if uFactor == 1:
        compileCommand = uCommand0 + appCommand0 + generalCommand
    elif uFactor == 2:
        compileCommand = uCommand2 + appCommand0 + generalCommand

    compileProc = subprocess.Popen([compileCommand, '-u'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (compileOut, compileErr) = compileProc.communicate()

    disassembleCommand = "llvm-dis-12 kernel.bc -o kernel.ll"
    disassembleProc = subprocess.Popen(
        [disassembleCommand, '-u'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (disassembleOut, disassembleErr) = disassembleProc.communicate()

    if compileErr:
        print("Compile error message: ", compileErr)
    if disassembleErr:
        print("Disassemble error message: ", disassembleErr)
        return

    # collect the potentially targeting kernel/function from kernel.ll
    irFile = open('kernel.ll', 'r')
    irLines = irFile.readlines()

    # strips the newline character
    for line in irLines:
        if "define " in line and "{" in line and "@" in line:
            funcName = line.split("@")[1].split("(")[0]
            if "kernel" in funcName:
                targetKernel = funcName
                break

    irFile.close()
    return targetKernel


def DVFSMap(kernels,df):
    """
    This is a func for mapping kernels and gain information during mapping.

    Parameters: kernel name, df array to collect mapping information of kernels

    Returns: NULL
    """
    getMapCommand = "opt-12 -load ../build/src/libmapperPass.so -mapperPass kernel.bc"
    genMapProc = subprocess.Popen([getMapCommand, "-u"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    dataS = []    # for get results from subprocess and output to pandas
    kernelsSource = (kernels.split("."))[0]
    dataS.append(kernelsSource)

    try:
        eventlet.monkey_patch()
        with eventlet.Timeout(timeOutSet, True):
            with genMapProc.stdout:
                genMapProc.stdout.flush()
                for line in iter(genMapProc.stdout.readline, b''):
                    outputLine = line.decode("ISO-8859-1")
                    if "DFG node count: " in outputLine:
                        dataS.append(int(outputLine.split("DFG node count: ")[1].split(";")[0]))
                        dataS.append(int(outputLine.split("DFG edge count: ")[1].split(";")[0]))
                    if "[RecMII: " in outputLine:
                        dataS.append(int(outputLine.split("[RecMII: ")[1].split("]")[0]))
                    if "tile avg fu utilization: " in outputLine:
                        dataS.append(float(outputLine.split("avg overall utilization: ")[1].split("%")[0]))
                    if "histogram 0% tile utilization: " in outputLine:
                        dataS.append(int(outputLine.split("histogram 0% tile utilization: ")[1]))
                    if "tile average DVFS frequency level: " in outputLine:
                        dataS.append(float((outputLine.split("tile average DVFS frequency level: ")[1].split("%")[0])))
                    if "histogram 0% tile DVFS frequency ratio: " in outputLine:
                        dataS.append(int(outputLine.split("histogram 0% tile DVFS frequency ratio: ")[1]))
                    if "histogram 25% tile DVFS frequency ratio: " in outputLine:
                        dataS.append(int(outputLine.split("histogram 25% tile DVFS frequency ratio: ")[1]))
                    if "histogram 50% tile DVFS frequency ratio: " in outputLine:
                        dataS.append(int(outputLine.split("histogram 50% tile DVFS frequency ratio: ")[1]))
                    if "histogram 100% tile DVFS frequency ratio: " in outputLine:
                        dataS.append(int(outputLine.split("histogram 100% tile DVFS frequency ratio: ")[1]))
                    
    except eventlet.timeout.Timeout:
        dataS = [0]*(dictColumn)
        print("Skipping a specific config for kernel: ", kernels)

    df.loc[len(df.index)] = dataS


def showTableI(cvsPath, nameBaselineS):
    '''
    This is a func to generate information of kernels in cvs.

    Parameters: path of cvs, information of kernels in baseline

    Returns: NULL
    '''

    # read nodes, edges, and RecMII of 6x6_unroll1/unroll2_baseline
    nameBaselineS.index(fileBaselineU1) # to check if the file name is correct
    nameBaselineS.index(fileBaselineU2) # to check if the file name is correct
    df = pd.read_csv(fileBaselineU1)
    yNodesU1 = df['DFG nodes'].tolist()
    yNodesU1 = yNodesU1[1:]
    df = pd.read_csv(fileBaselineU2)
    yNodesU2 = df['DFG nodes'].tolist()
    yNodesU2 = yNodesU2[1:]
    df = pd.read_csv(fileBaselineU1)
    yEdgesU1 = df['DFG edges'].tolist()
    yEdgesU1 = yEdgesU1[1:]
    df = pd.read_csv(fileBaselineU2)
    yEdgesU2 = df['DFG edges'].tolist()
    yEdgesU2 = yEdgesU2[1:]
    df = pd.read_csv(fileBaselineU1)
    yRecMIIU1 = df['recMII'].tolist()
    yRecMIIU1 = yRecMIIU1[1:]
    df = pd.read_csv(fileBaselineU2)
    yRecMIIU2 = df['recMII'].tolist()
    yRecMIIU2 = yRecMIIU2[1:]
    tmpList = [yNodesU1, yEdgesU1, yRecMIIU1, yNodesU2, yEdgesU2, yRecMIIU2]
    transList = [[row[i] for row in tmpList] for i in range(len(tmpList[0]))]   # transposition

    # generate a cvs
    tableIDict = {'Kernel': "", 'Unroll1 Nodes': "", 'Unroll1 Edges': "", 'Unroll1 RecMII': "", 'Unroll2 Nodes': "", 'Unroll2 Edges': "", 'Unroll2 RecMII': ""}
    tableIDictColumn = len(tableIDict)
    df = pd.DataFrame(tableIDict, index=[0])
    dfBenchs = [[0] * (tableIDictColumn - 1) for _ in range(testBenchsNum)]  # a two-dim list with testBenchsNum of Rows 
    for i in range(testBenchsNum):
        tmpList = [0]
        tmpList[0] = testBenchs[i]  # add kernel name in the head of list
        tmpList.extend(transList[i])    # add information of current kernel 
        dfBenchs[i] = tmpList    
    for i in range(testBenchsNum):
        df.loc[len(df.index)] = dfBenchs[i]
    df.to_csv(cvsPath)
 

def showFig9(figPath, nameBaselineS, namePertileS, nameIcedS):
    '''
    This is a func to generate Parallel Bar Chart (Figure 9) in png.

    Parameters: path of figure, Y-axis data

    Returns: NULL
    '''
    # read avg tile utilization of 6x6_unroll1/unroll2_baseline
    nameBaselineS.index(fileBaselineU1) # to check if the file name is correct
    nameBaselineS.index(fileBaselineU2) # to check if the file name is correct
    df = pd.read_csv(fileBaselineU1)
    yBaselineU1 = df['avg tile utilization'].tolist()
    yBaselineU1 = yBaselineU1[1:]
    df = pd.read_csv(fileBaselineU2)
    yBaselineU2 = df['avg tile utilization'].tolist()
    yBaselineU2 = yBaselineU2[1:]
    # read avg tile utilization of 6x6_unroll1/unroll2_pertile
    namePertileS.index(filePertileU1) # to check if the file name is correct
    namePertileS.index(filePertileU2) # to check if the file name is correct    
    df = pd.read_csv(filePertileU1)
    yPertileU1 = df['avg tile utilization'].tolist()
    yPertileU1 = yPertileU1[1:]
    df = pd.read_csv(filePertileU2)
    yPertileU2 = df['avg tile utilization'].tolist()
    yPertileU2 = yPertileU2[1:]
    # read avg tile utilization of 6x6_unroll1/unroll2_iced
    nameIcedS.index(fileIcedU1) # to check if the file name is correct
    nameIcedS.index(fileIcedU2) # to check if the file name is correct     
    df = pd.read_csv(fileIcedU1)
    yIcedU1 = df['avg tile utilization'].tolist()
    yIcedU1 = yIcedU1[1:]
    df = pd.read_csv(fileIcedU2)
    yIcedU2 = df['avg tile utilization'].tolist()
    yIcedU2 = yIcedU2[1:]

    # draw a 6 bar chart
    plt.figure(figsize=(16, 5))
    x = np.arange(len(testBenchs))  # X-axis
    xWidth = 0.1   # width of every bar 
    plt.bar(x - xWidth*2.5, yBaselineU1, xWidth, label='Baseline Unroll1')
    plt.bar(x - xWidth*1.5, yPertileU1, xWidth, label='Per-tile DVFS + Power-gating Unroll1')
    plt.bar(x - xWidth*0.5, yIcedU1, xWidth, label='ICED Unroll1')
    plt.bar(x + xWidth*0.5, yBaselineU2, xWidth, label='Baseline Unroll2')
    plt.bar(x + xWidth*1.5, yPertileU2, xWidth, label='Per-tile DVFS + Power-gating Unroll2')
    plt.bar(x + xWidth*2.5, yIcedU2, xWidth, label='ICED Unroll2')
    plt.title('ExampleFig9')
    plt.ylabel('Avg utilization')
    plt.xticks(x, labels=testBenchs)
    plt.legend()
    plt.savefig(figPath)


def showFig10(figPath, nameBaselineS, namePertileS, nameIcedS):
    '''
    This is a func to generate Parallel Bar Chart (Figure 10) in png.

    Parameters: path of figure, Y-axis data

    Returns: NULL
    '''

    # read avg tile frequency of 6x6_unroll1/unroll2_baseline  
    nameBaselineS.index(fileBaselineU1) # to check if the file name is correct
    nameBaselineS.index(fileBaselineU2) # to check if the file name is correct
    df = pd.read_csv(fileBaselineU1)
    yBaselineU1 = df['avg tile frequency'].tolist()
    yBaselineU1 = yBaselineU1[1:]
    df = pd.read_csv(fileBaselineU2)
    yBaselineU2 = df['avg tile frequency'].tolist()
    yBaselineU2 = yBaselineU2[1:]
    # read avg tile frequency of 6x6_unroll1/unroll2_pertile    
    namePertileS.index(filePertileU1) # to check if the file name is correct
    namePertileS.index(filePertileU2) # to check if the file name is correct    
    df = pd.read_csv(filePertileU1)
    yPertileU1 = df['avg tile frequency'].tolist()
    yPertileU1 = yPertileU1[1:]
    df = pd.read_csv(filePertileU2)
    yPertileU2 = df['avg tile frequency'].tolist()
    yPertileU2 = yPertileU2[1:]
    # read avg tile frequency of 6x6_unroll1/unroll2_iced
    nameIcedS.index(fileIcedU1) # to check if the file name is correct
    nameIcedS.index(fileIcedU2) # to check if the file name is correct     
    df = pd.read_csv(fileIcedU1)
    yIcedU1 = df['avg tile frequency'].tolist()
    yIcedU1 = yIcedU1[1:]
    df = pd.read_csv(fileIcedU2)
    yIcedU2 = df['avg tile frequency'].tolist()
    yIcedU2 = yIcedU2[1:]

    # draw a 6 bar chart
    plt.figure(figsize=(16, 5))
    x = np.arange(len(testBenchs))  # X-axis
    xWidth = 0.1   # width of every bar 
    plt.bar(x - xWidth*2.5, yBaselineU1, xWidth, label='Baseline Unroll1')
    plt.bar(x - xWidth*1.5, yPertileU1, xWidth, label='Per-tile DVFS + Power-gating Unroll1')
    plt.bar(x - xWidth*0.5, yIcedU1, xWidth, label='ICED Unroll1')
    plt.bar(x + xWidth*0.5, yBaselineU2, xWidth, label='Baseline Unroll2')
    plt.bar(x + xWidth*1.5, yPertileU2, xWidth, label='Per-tile DVFS + Power-gating Unroll2')
    plt.bar(x + xWidth*2.5, yIcedU2, xWidth, label='ICED Unroll2')
    plt.title('ExampleFig10')
    plt.ylabel('Avg DVFS Level')
    plt.xticks(x, labels=testBenchs)
    plt.legend()
    plt.savefig(figPath)


def showFig11(figPath, nameBaselineS, namePertileS, nameIcedS):
    '''
    This is a func to caculate the power from given information and generate Parallel Bar Chart (Figure 11) in png.

    Parameters: path of figure, Y-axis data

    Returns: NULL
    '''

    # STATIC POWER VARIBLES
    # for tiles with 100% DVFS level: c = 7.484220158, v100 = 0.7, f100 = 0.43478
    c = 7.484220158; v100 = 0.7; f100 = 0.43478
    # for tiles with 50% DVFS level: c = 7.484220158, v50 = 0.504, f50 = 0.21739
    v50 = 0.504; f50 = 0.21739
    # for tiles with 25% DVFS level: c = 7.484220158, v25 = 0.42, f25 = 0.108695
    v25 = 0.42; f25 = 0.108695
    # power of other conponents
    tile_static_power = 1.121; sram_power = 62.653; control_overhead_DVFS = 2.46
    # Total power = (tile_power) of all tiles + sram_power + control_overhead_DVFS.  
    # For each tile, tile_power = dynamic_power + tile_static_power = cv^2f + 1.121.

    # read number_of_idle_tiles of 6x6_unroll1/unroll2_baseline
    nameBaselineS.index(fileBaselineU1) # to check if the file name is correct
    nameBaselineS.index(fileBaselineU2) # to check if the file name is correct
    df = pd.read_csv(fileBaselineU1)
    number_of_idle_tiles_U1 = df['0% tiles u'].tolist()
    number_of_idle_tiles_U1 = number_of_idle_tiles_U1[1:]
    df = pd.read_csv(fileBaselineU2)
    number_of_idle_tiles_U2 = df['0% tiles u'].tolist()
    number_of_idle_tiles_U2 = number_of_idle_tiles_U2[1:]
    # read number_of_100/50/25/0_DVFS_tiles of 6x6_unroll1/unroll2_pertile
    namePertileS.index(filePertileU1) # to check if the file name is correct
    namePertileS.index(filePertileU2) # to check if the file name is correct    
    df = pd.read_csv(filePertileU1)
    number_of_100_DVFS_tiles_Pertile_U1 = df['100% tiles f'].tolist()
    number_of_100_DVFS_tiles_Pertile_U1 = number_of_100_DVFS_tiles_Pertile_U1[1:]
    df = pd.read_csv(filePertileU2)
    number_of_100_DVFS_tiles_Pertile_U2 = df['100% tiles f'].tolist()
    number_of_100_DVFS_tiles_Pertile_U2 = number_of_100_DVFS_tiles_Pertile_U2[1:]
    df = pd.read_csv(filePertileU1)
    number_of_50_DVFS_tiles_Pertile_U1 = df['50% tiles f'].tolist()
    number_of_50_DVFS_tiles_Pertile_U1 = number_of_50_DVFS_tiles_Pertile_U1[1:]
    df = pd.read_csv(filePertileU2)
    number_of_50_DVFS_tiles_Pertile_U2 = df['50% tiles f'].tolist()
    number_of_50_DVFS_tiles_Pertile_U2 = number_of_50_DVFS_tiles_Pertile_U2[1:]
    df = pd.read_csv(filePertileU1)
    number_of_25_DVFS_tiles_Pertile_U1 = df['25% tiles f'].tolist()
    number_of_25_DVFS_tiles_Pertile_U1 = number_of_25_DVFS_tiles_Pertile_U1[1:]
    df = pd.read_csv(filePertileU2)
    number_of_25_DVFS_tiles_Pertile_U2 = df['25% tiles f'].tolist()
    number_of_25_DVFS_tiles_Pertile_U2 = number_of_25_DVFS_tiles_Pertile_U2[1:]
    df = pd.read_csv(filePertileU1)
    number_of_0_DVFS_tiles_Pertile_U1 = df['0% tiles f'].tolist()
    number_of_0_DVFS_tiles_Pertile_U1 = number_of_0_DVFS_tiles_Pertile_U1[1:]
    df = pd.read_csv(filePertileU2)
    number_of_0_DVFS_tiles_Pertile_U2 = df['0% tiles f'].tolist()
    number_of_0_DVFS_tiles_Pertile_U2 = number_of_0_DVFS_tiles_Pertile_U2[1:]
    # read number_of_100/50/25_DVFS_tiles of 6x6_unroll1/unroll2_iced
    nameIcedS.index(fileIcedU1) # to check if the file name is correct
    nameIcedS.index(fileIcedU2) # to check if the file name is correct 
    df = pd.read_csv(fileIcedU1)
    number_of_100_DVFS_tiles_Iced_U1 = df['100% tiles f'].tolist()
    number_of_100_DVFS_tiles_Iced_U1 = number_of_100_DVFS_tiles_Iced_U1[1:]
    df = pd.read_csv(fileIcedU2)
    number_of_100_DVFS_tiles_Iced_U2 = df['100% tiles f'].tolist()
    number_of_100_DVFS_tiles_Iced_U2 = number_of_100_DVFS_tiles_Iced_U2[1:]
    df = pd.read_csv(fileIcedU1)
    number_of_50_DVFS_tiles_Iced_U1 = df['50% tiles f'].tolist()
    number_of_50_DVFS_tiles_Iced_U1 = number_of_50_DVFS_tiles_Iced_U1[1:]
    df = pd.read_csv(fileIcedU2)
    number_of_50_DVFS_tiles_Iced_U2 = df['50% tiles f'].tolist()
    number_of_50_DVFS_tiles_Iced_U2 = number_of_50_DVFS_tiles_Iced_U2[1:]
    df = pd.read_csv(fileIcedU1)
    number_of_25_DVFS_tiles_Iced_U1 = df['25% tiles f'].tolist()
    number_of_25_DVFS_tiles_Iced_U1 = number_of_25_DVFS_tiles_Iced_U1[1:]
    df = pd.read_csv(fileIcedU2)
    number_of_25_DVFS_tiles_Iced_U2 = df['25% tiles f'].tolist()
    number_of_25_DVFS_tiles_Iced_U2 = number_of_25_DVFS_tiles_Iced_U2[1:]


    # caculate corresponding power using the information above
    # Baseline: Power (36 tiles with SRAM) = 36 * (c * v100^2 * f100 + tile_static_power) + 62.653 = 36 * 2.715 + 62.653 = 160.41. 
    # Baseline: The v/f we use the 100% DVFS set and there is no control_overhead_DVFS for baseline.
    yBaselineU1 = [36 * (c * v100**2 * f100 + tile_static_power) + sram_power]*testBenchsNum    # *testBenchsNum: all Y-axi data must match testBenchsNum
    yBaselineU2 = [36 * (c * v100**2 * f100 + tile_static_power) + sram_power]*testBenchsNum
    # Baseline + Power-gating: Power = power_of_baseline - number_of_idle_tiles * (c * v100^2 * f100 + tile_static_power). The number_of_idle_tiles is number_of_0%_utilization_tiles.
    yBaselinePGU1 = [0]*testBenchsNum; yBaselinePGU2 = [0]*testBenchsNum
    for i in range(testBenchsNum):
        yBaselinePGU1[i] = yBaselineU1[i] - number_of_idle_tiles_U1[i] * (c * v100**2 * f100 + tile_static_power)
        yBaselinePGU2[i] = yBaselineU2[i] - number_of_idle_tiles_U2[i] * (c * v100**2 * f100 + tile_static_power)
    # Per-tile DVFS + Power-gating: Power = number_of_100%_DVFS_tiles * (c * v100^2 * f100) + number_of_50%_DVFS_tiles * (c * v50^2 * f50) + 
    # number_of_25%_DVFS_tiles * (c * v25^2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * (36 - number_of_0%_DVFS_tiles).
    yPertileU1 = [0]*testBenchsNum; yPertileU2 = [0]*testBenchsNum
    for i in range(testBenchsNum):
        yPertileU1[i] = number_of_100_DVFS_tiles_Pertile_U1[i] * (c * v100**2 * f100) + number_of_50_DVFS_tiles_Pertile_U1[i] * (c * v50**2 * f50) + \
        number_of_25_DVFS_tiles_Pertile_U1[i] * (c * v25**2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * (36 - number_of_0_DVFS_tiles_Pertile_U1[i])
        yPertileU2[i] = number_of_100_DVFS_tiles_Pertile_U2[i] * (c * v100**2 * f100) + number_of_50_DVFS_tiles_Pertile_U2[i] * (c * v50**2 * f50) + \
        number_of_25_DVFS_tiles_Pertile_U2[i] * (c * v25**2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * (36 - number_of_0_DVFS_tiles_Pertile_U2[i])

    print(number_of_0_DVFS_tiles_Pertile_U1)
    # ICED: Power = number_of_100%_DVFS_tiles * (c * v100^2 * f100) + number_of_50%_DVFS_tiles * (c * v50^2 * f50) + 
    # number_of_25%_DVFS_tiles * (c * v25^2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * 9.
    yIcedU1 = [0]*testBenchsNum; yIcedU2 = [0]*testBenchsNum
    for i in range(testBenchsNum):
        yIcedU1 = number_of_100_DVFS_tiles_Iced_U1[i] * (c * v100**2 * f100) + number_of_50_DVFS_tiles_Iced_U1[i] * (c * v50**2 * f50) + \
        number_of_25_DVFS_tiles_Iced_U1[i] * (c * v25**2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * 9
        yIcedU2 = number_of_100_DVFS_tiles_Iced_U2[i] * (c * v100**2 * f100) + number_of_50_DVFS_tiles_Iced_U2[i] * (c * v50**2 * f50) + \
        number_of_25_DVFS_tiles_Iced_U2[i] * (c * v25**2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * 9

    # draw a 8 bar chart
    plt.figure(figsize=(16, 5))
    x = np.arange(len(testBenchs))  # X-axis
    xWidth = 0.1   # width of every bar 
    plt.bar(x - xWidth*3.5, yBaselineU1, xWidth, label='Baseline Unroll1')
    plt.bar(x - xWidth*2.5, yBaselinePGU1, xWidth, label='Baseline + Power-gating Unroll1')
    plt.bar(x - xWidth*1.5, yPertileU1, xWidth, label='Per-tile DVFS + Power-gating Unroll1')
    plt.bar(x - xWidth*0.5, yIcedU1, xWidth, label='ICED Unroll1')
    plt.bar(x + xWidth*0.5, yBaselineU2, xWidth, label='Baseline Unroll2')
    plt.bar(x + xWidth*1.5, yBaselinePGU2, xWidth, label='Baseline + Power-gating Unroll2')
    plt.bar(x + xWidth*2.5, yPertileU2, xWidth, label='Per-tile DVFS + Power-gating Unroll2')
    plt.bar(x + xWidth*3.5, yIcedU2, xWidth, label='ICED Unroll2')
    plt.title('ExampleFig11')
    plt.ylabel('Avg Power(mW)')
    plt.xticks(x, labels=testBenchs)
    plt.legend()
    plt.savefig(figPath)


def showFig12(figPath, nameBaselineS, namePertileS, nameIcedS):
    '''
    This is a func to caculate the power from given information and generate Parallel Bar Chart (Figure 12) in png.

    Parameters: path of figure, Y-axis data

    Returns: NULL
    '''
    # read avg tile frequency of 2x2/4x4/unroll1_pertile and 6x6/8x8_unroll1/unroll2_pertile
    yPertile=[]
    for namePertile in namePertileS:
        df = pd.read_csv(namePertile)
        tmpList = df['avg tile frequency'].tolist()
        yPertile.extend(tmpList)
    yPertileX2U1 = yPertile[1:1+testBenchsNum]
    yPertileX4U1 = yPertile[2+testBenchsNum:2+2*testBenchsNum]
    yPertileX6U1 = yPertile[3+2*testBenchsNum:3+3*testBenchsNum]
    yPertileX6U2 = yPertile[4+3*testBenchsNum:4+4*testBenchsNum]
    yPertileX8U1 = yPertile[5+4*testBenchsNum:5+5*testBenchsNum]
    yPertileX8U2 = yPertile[6+5*testBenchsNum:6+6*testBenchsNum]
    # read avg tile frequency of 2x2/4x4/unroll1_pertile and 6x6/8x8_unroll1/unroll2_iced
    yIced=[]
    for nameIced in nameIcedS:
        df = pd.read_csv(nameIced)
        tmpList = df['avg tile frequency'].tolist()
        yIced.extend(tmpList)
    yIcedX2U1 = yIced[1:1+testBenchsNum]
    yIcedX4U1 = yIced[2+testBenchsNum:2+2*testBenchsNum]
    yIcedX6U1 = yIced[3+2*testBenchsNum:3+3*testBenchsNum]
    yIcedX6U2 = yIced[4+3*testBenchsNum:4+4*testBenchsNum]
    yIcedX8U1 = yIced[5+4*testBenchsNum:5+5*testBenchsNum]
    yIcedX8U2 = yIced[6+5*testBenchsNum:6+6*testBenchsNum]

    # draw a 12 bar chart
    plt.figure(figsize=(16, 5))
    x = np.arange(len(testBenchs))  # X-axis
    xWidth = 0.05   # width of every bar 
    plt.bar(x - xWidth*5.5, yPertileX2U1, xWidth, label='Per-tile DVFS + Power-gating, 2x2_Unroll1')
    plt.bar(x - xWidth*4.5, yPertileX4U1, xWidth, label='Per-tile DVFS + Power-gating, 4x4_Unroll1')
    plt.bar(x - xWidth*3.5, yPertileX6U1, xWidth, label='Per-tile DVFS + Power-gating, 6x6_Unroll1')
    plt.bar(x - xWidth*2.5, yPertileX6U2, xWidth, label='Per-tile DVFS + Power-gating, 6x6_Unroll2')
    plt.bar(x - xWidth*1.5, yPertileX8U1, xWidth, label='Per-tile DVFS + Power-gating, 8x8_Unroll1')
    plt.bar(x - xWidth*0.5, yPertileX8U2, xWidth, label='Per-tile DVFS + Power-gating, 8x8_Unroll2')
    plt.bar(x + xWidth*0.5, yIcedX2U1, xWidth, label='ICED, 2x2_Unroll1')
    plt.bar(x + xWidth*1.5, yIcedX4U1, xWidth, label='ICED, 4x4_Unroll1')
    plt.bar(x + xWidth*2.5, yIcedX6U1, xWidth, label='ICED, 6x6_Unroll1')
    plt.bar(x + xWidth*3.5, yIcedX6U2, xWidth, label='ICED, 6x6_Unroll2')
    plt.bar(x + xWidth*4.5, yIcedX8U1, xWidth, label='ICED, 8x8_Unroll1')
    plt.bar(x + xWidth*5.5, yIcedX8U2, xWidth, label='ICED, 8x8_Unroll2')
    plt.title('ExampleFig12')
    plt.ylabel('Avg DVFS Level')
    plt.xticks(x, labels=testBenchs)
    plt.legend()
    plt.savefig(figPath)


def fig091011GenerationKernel():
    '''
    This is a func to repalce the correct testBenchs for showFig9(), showFig10() and showFig11(), since fft.c, spmv.c and mvt.c is not appliable in "./tmp/t_6x6_unroll2_iced.csv".
    '''
    global testBenchs 
    testBenchs = ["fir.cpp", "latnrm.c", "dtw.cpp", "conv.c", "relu.c", "histogram.cpp", "gemm.c"] # the file type of kernels must match
    global testBenchsNum
    testBenchsNum = len(testBenchs)


def fig12GenerationKernel():
    '''
    This is a func to repalce the correct testBenchs for showFig12() since fft.c, dtw.cpp, spmv.c and mvt.c is not appliable in 2x2 and 4x4 CGRA.
    '''
    global testBenchs 
    testBenchs = ["fir.cpp", "latnrm.c", "conv.c", "relu.c", "histogram.cpp", "gemm.c"]
    global testBenchsNum
    testBenchsNum = len(testBenchs)

# ----------------------------------------------------------------------------
#   main function in testT3forDVFS.py                                       /
# ----------------------------------------------------------------------------

def mainBaseline(Crows, Columns, uFactor, do_mapping = True):
    """
    This is a func to compile, run and map kernels under param_baseline.json.

    Parameters: rows and columns of the mapped CGRA, unrollFactor

    Returns: name of the cvs that collects information of mapped kernels 
    """
    csvName = './tmp/t_' + str(Crows) + 'x' + str(Columns) + '_unroll' + str(uFactor) + '_baseline.csv'
    print("Generating", csvName)
    df = pd.DataFrame(dictCvs, index=[0])

    for kernels in testBenchs:
        if kernels == "NULL":
            dataS = [""]*dictColumn
            df.loc[len(df.index)] = dataS
            continue

        targetKernel = DVFSComp(kernels, uFactor)

        genBaselineJson = {
            "kernel": targetKernel,
            "targetFunction": False,
            "targetNested": False,
            "targetLoopsID": [0],
            "doCGRAMapping": True,
            "row": Crows,
            "column": Columns,
            "precisionAware": False,
            "heterogeneity": False,
            "isTrimmedDemo": True,
            "heuristicMapping": True,
            "parameterizableCGRA": False,
            "diagonalVectorization": False,
            "bypassConstraint": 16,
            "isStaticElasticCGRA": False,
            "ctrlMemConstraint": 100,
            "regConstraint": 20,
            "supportDVFS": False,
            "DVFSIslandDim": 1,
            "DVFSAwareMapping": False,
            "enablePowerGating": False
        }

        json_object = json.dumps(genBaselineJson, indent=4)

        with open(jsonName, "w") as outfile:
            outfile.write(json_object)

        DVFSMap(kernels, df)

    df.to_csv(csvName)
    return csvName


def mainPertile(Crows, Columns, uFactor):
    """
    This is a func to compile, run and map kernels under param_pertile.json.

    Parameters: rows and columns of the mapped CGRA, unrollFactor

    Returns: name of the cvs that collects information of mapped kernels 
    """
    csvName = './tmp/t_' + str(Crows) + 'x' + str(Columns) + '_unroll' + str(uFactor) + '_pertile.csv'
    print("Generating", csvName)
    df = pd.DataFrame(dictCvs, index=[0])

    for kernels in testBenchs:
        if kernels == "NULL":
            dataS = [""]*dictColumn
            df.loc[len(df.index)] = dataS
            continue

        targetKernel = DVFSComp(kernels, uFactor)

        genPertileJson = {
            "kernel": targetKernel,
            "targetFunction": False,
            "targetNested": False,
            "targetLoopsID": [0],
            "doCGRAMapping": True,
            "row": Crows,
            "column": Columns,
            "precisionAware": False,
            "heterogeneity": False,
            "isTrimmedDemo": True,
            "heuristicMapping": True,
            "parameterizableCGRA": False,
            "diagonalVectorization": False,
            "bypassConstraint": 16,
            "isStaticElasticCGRA": False,
            "ctrlMemConstraint": 100,
            "regConstraint": 20,
            "supportDVFS": True,
            "DVFSIslandDim": 1,
            "DVFSAwareMapping": False,
            "enablePowerGating": True
        }
        json_object = json.dumps(genPertileJson, indent=4)

        with open(jsonName, "w") as outfile:
            outfile.write(json_object)

        DVFSMap(kernels, df)

    df.to_csv(csvName)
    return csvName


def mainIced(Crows, Columns, uFactor):
    """
    This is a func to compile, run and map kernels under param_iced.json.

    Parameters: rows and columns of the mapped CGRA, unrollFactor

    Returns: name of the cvs that collects information of mapped kernels 
    """
    csvName = './tmp/t_' + str(Crows) + 'x' + str(Columns) + '_unroll' + str(uFactor) + '_iced.csv'
    print("Generating", csvName)
    df = pd.DataFrame(dictCvs, index=[0])

    for kernels in testBenchs:
        if kernels == "NULL":
            dataS = [""]*dictColumn
            df.loc[len(df.index)] = dataS
            continue

    for kernels in testBenchs:
        if kernels == "NULL":
            continue

        targetKernel = DVFSComp(kernels, uFactor)

        genIcedJson = {
            "kernel": targetKernel,
            "targetFunction": False,
            "targetNested": False,
            "targetLoopsID": [0],
            "doCGRAMapping": True,
            "row": Crows,
            "column": Columns,
            "precisionAware": False,
            "heterogeneity": False,
            "isTrimmedDemo": True,
            "heuristicMapping": True,
            "parameterizableCGRA": False,
            "diagonalVectorization": False,
            "bypassConstraint": 16,
            "isStaticElasticCGRA": False,
            "ctrlMemConstraint": 100,
            "regConstraint": 20,
            "supportDVFS": True,
            "DVFSIslandDim": 2,
            "DVFSAwareMapping": True,
            "enablePowerGating": True
        }

        json_object = json.dumps(genIcedJson, indent=4)

        with open(jsonName, "w") as outfile:
            outfile.write(json_object)

        DVFSMap(kernels, df)

    df.to_csv(csvName)
    return csvName


def main():
    """
    This is the main function that runs testBenchs with selected CGRA size and unrolling factor, then outputs result in png or in cvs.

    Parameters: NULL

    Returns: NULL
    """
    print("ICEDdemo.py starts running.")
    timeStart = time.time()
    CGRAsizes = [6]  # the mapped CGRA size = 6
    unrollFactors = [1, 2]   # unrolling factor = 1, 2
    nameCvsBaseline = []    
    cvsPath = ""
    for CGRAsize in CGRAsizes:
        for unrollFactor in unrollFactors:      
            nameCvsBaseline.append(mainBaseline(CGRAsize, CGRAsize, unrollFactor, False)) 
    print("Generating Table I: Target workloads and streaming applications")
    cvsPath = "./example/exampleTable.cvs"
    showTableI(cvsPath, nameCvsBaseline)

    print("Replace testBenchs to generate Fig. 9, 10, 11.")
    # fig091011GenerationKernel()
    CGRAsizes = [6]  # the mapped CGRA size = 6
    unrollFactors = [1, 2]   # unrolling factor = 1, 2
    nameCvsBaseline = []    
    nameCvsPertile = []   
    nameCvsIced = []    
    figPath = ""
    for CGRAsize in CGRAsizes:
        for unrollFactor in unrollFactors:      
            nameCvsBaseline.append(mainBaseline(CGRAsize, CGRAsize, unrollFactor))
            nameCvsPertile.append(mainPertile(CGRAsize, CGRAsize, unrollFactor))
            nameCvsIced.append(mainIced(CGRAsize, CGRAsize, unrollFactor))  
    print("Generating Fig. 9: Average utilization of tiles across different kernels")
    figPath = "./example/exampleFig9.png"
    showFig9(figPath, nameCvsBaseline, nameCvsPertile, nameCvsIced)   

    print("Generating Fig. 10: Average DVFS level across different kernels")
    figPath = "./example/exampleFig10.png"
    showFig10(figPath, nameCvsBaseline, nameCvsPertile, nameCvsIced)   

    print("Generating Fig. 11: Evaluation of energy-efficiency")
    figPath = "./example/exampleFig11.png"
    showFig11(figPath, nameCvsBaseline, nameCvsPertile, nameCvsIced)

    print("Replace testBenchs to generate Fig. 12.") 
    # fig12GenerationKernel()
    CGRAsizes = [2, 4, 6, 8]  # the mapped CGRA size = 2, 4, 6, 8
    unrollFactors = [1, 2]   # unrolling factor = 1, 2
    nameCvsBaseline = []    
    nameCvsPertile = []   
    nameCvsIced = []    
    figPath = ""
    for CGRAsize in CGRAsizes:
        for unrollFactor in unrollFactors: 
            if (CGRAsize == 2 and unrollFactor == 2) or (CGRAsize == 4 and unrollFactor == 2):
                continue             
            nameCvsBaseline.append(mainBaseline(CGRAsize, CGRAsize, unrollFactor))
            nameCvsPertile.append(mainPertile(CGRAsize, CGRAsize, unrollFactor))
            nameCvsIced.append(mainIced(CGRAsize, CGRAsize, unrollFactor))     
    print("Generating Fig. 12: Evaluation of scalability") 
    figPath = "./example/exampleFig12.png"
    showFig12(figPath, nameCvsBaseline, nameCvsPertile, nameCvsIced)

    print("DONE. Time cost: ", time.time() - timeStart, "s")

# ----------------------------------------------------------------------------
#   run main in testT3forDVFS.py                                            /
# ----------------------------------------------------------------------------

main()
