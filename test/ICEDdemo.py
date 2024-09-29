# ----------------------------------------------------------------------------
#   Filename: ICEDdemo.py                                                   /
#   Description: python script of ICED                                      /
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
#   global variables                                                        /
# ----------------------------------------------------------------------------

testBenchs = ["fir.cpp", "latnrm.c", "fft.c", "dtw.cpp", "spmv.c", "conv.c", "relu.c", "histogram.cpp", "mvt.c", "gemm.c",  "aggregate1.c", "aggregate2.c", "combine.c", "combineRelu.c", "compress.cpp", "pooling.c", "decompose.cpp", "determinant.cpp", "init.cpp", "invert.cpp", "solver0.cpp", "solver1.cpp"] # the file type of kernels must match
testBenchsNum = len(testBenchs)
dictCsv = {'kernels': "", 'DFG nodes': "", 'DFG edges': "", 'recMII': "", 'mappingII': "", 'avg tile utilization': "", '0% tiles u': "", 'avg tile frequency': "",	'0% tiles f': "", 
'25% tiles f': "",'50% tiles f': "", '100% tiles f': ""}  # column names of generated CSV
dictColumn = len(dictCsv)
jsonName = "./param.json"   # name of generated json file
timeOutSet = 180   # set Timeout = 3 minutes
# for showTable(), showFig9(), showFig10(), showFig11() since they all read the 6x6_*_*.csv
fileBaselineU1 = "./tmp/t_6x6_unroll1_baseline.csv"  
fileBaselineU2 = "./tmp/t_6x6_unroll2_baseline.csv"   
filePertileU1 = "./tmp/t_6x6_unroll1_pertile.csv"
filePertileU2 = "./tmp/t_6x6_unroll2_pertile.csv"  
fileIcedU1 = "./tmp/t_6x6_unroll1_iced.csv"
fileIcedU2 = "./tmp/t_6x6_unroll2_iced.csv"

# For your convience, the names of csv are listed to avoid wating for the csv generation in main function.
# nameCsvBaseline = ["./tmp/t_2x2_unroll1_baseline.csv", "./tmp/t_4x4_unroll1_baseline.csv", "./tmp/t_6x6_unroll1_baseline.csv", 
# "./tmp/t_6x6_unroll2_baseline.csv", "./tmp/t_8x8_unroll1_baseline.csv", "./tmp/t_8x8_unroll2_baseline.csv"]
# nameCsvPertile = ["./tmp/t_2x2_unroll1_pertile.csv", "./tmp/t_4x4_unroll1_pertile.csv", "./tmp/t_6x6_unroll1_pertile.csv", 
# "./tmp/t_6x6_unroll2_pertile.csv", "./tmp/t_8x8_unroll1_pertile.csv", "./tmp/t_8x8_unroll2_pertile.csv"]
# nameCsvIced = ["./tmp/t_2x2_unroll1_iced.csv", "./tmp/t_4x4_unroll1_iced.csv","./tmp/t_6x6_unroll1_iced.csv", 
# "./tmp/t_6x6_unroll2_iced.csv", "./tmp/t_8x8_unroll1_iced.csv", "./tmp/t_8x8_unroll2_iced.csv"] 

# ----------------------------------------------------------------------------
#   function defination                                                     /
# ----------------------------------------------------------------------------

def DVFSComp(fileName, uFactor):
    """
    This is a func compile a kernel using clang with selected unrolling factor.

    Parameters: file name of a kernel, unrolling factor

    Returns: function name of given kernel 
    """
    fileSource = (fileName.split("."))[0]

    uCommand0 = "clang-12 -emit-llvm -fno-unroll-loops -O3 -o kernel.bc -c "    # no unroll, i.e. unroll = 1
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
        print("Compile warning message: ", compileErr)  
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


def DVFSMap(kernel,df):
    """
    This is a func for mapping a kernel and gain information during mapping.

    Parameters: file name of a kernel, df array to collect mapping information of the kernel

    Returns: NULL
    """
    getMapCommand = "opt-12 -load ../build/src/libmapperPass.so -mapperPass kernel.bc"
    genMapProc = subprocess.Popen([getMapCommand, "-u"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    dataS = []    # for get results from subprocess and output to pandas
    kernelsSource = (kernel.split("."))[0]
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
                    if "[Mapping II: " in outputLine:
                        dataS.append(int(outputLine.split("[Mapping II: ")[1].split("]")[0]))
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
        # print("Skipping a specific config for kernel: ", kernel, "Because it runs more than", timeOutSet/60 , "minute(s).")
        dataS = [0]*(dictColumn)

    df.loc[len(df.index)] = dataS


def DVFSGen(kernel, df):
    """
    This is a func gain DFG information only for showTableI().

    Parameters: file name of a kernel, df array to collect mapping information of the kernel

    Returns: NULL
    """
    getMapCommand = "opt-12 -load ../build/src/libmapperPass.so -mapperPass kernel.bc"
    genMapProc = subprocess.Popen([getMapCommand, "-u"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    dataS = []    # for get results from subprocess and output to pandas
    kernelsSource = (kernel.split("."))[0]
    dataS.append(kernelsSource)
    DataSHead = 4   # the first 4 element of dataS is not empty: kernelsSource, DFG node count, DFG edge count, RecMII

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
                        dataS.extend([0]*(dictColumn-dataSHead))
                        break
                    
    except eventlet.timeout.Timeout:
        dataS = [0]*(dictColumn)
        print("Skipping a specific config for kernel: ", kernel, "Because it runs more than", timeOutSet/60 , "minute(s).")

    df.loc[len(df.index)] = dataS


def findMinII(baselineII, pertileII, icedII):
    """
    This is a func to find positive minII from three different IIs.

    Parameters: baselineII, pertileII, icedII

    Returns: minII
    """ 
    minII = []   
    for a, b, c in zip(baselineII, pertileII, icedII):
        # focus on positive minII
        positiveII = [tmpII for tmpII in (a, b, c) if tmpII > 0]
        minII.append(min(positiveII) if positiveII else None)

    return minII


def showTableI(csvPath, nameBaselineS):
    '''
    This is a func to read DFG nodes, edges, and RecMII from 6x6_*_baseline.csv and generate Table in csv.

    Parameters: path of csv, information of kernels in baseline

    Returns: NULL
    '''

    # read nodes, edges, and RecMII of 6x6_unroll1/unroll2_baseline.csv
    nameBaselineS.index(fileBaselineU1) # to check if the file name is correct
    nameBaselineS.index(fileBaselineU2) # to check if the file name is correct
    df = pd.read_csv(fileBaselineU1)
    yNodesU1 = df['DFG nodes'].tolist()[1:]
    yEdgesU1 = df['DFG edges'].tolist()[1:]
    yRecMIIU1 = df['recMII'].tolist()[1:]
    df = pd.read_csv(fileBaselineU2)
    yNodesU2 = df['DFG nodes'].tolist()[1:]
    yEdgesU2 = df['DFG edges'].tolist()[1:]
    yRecMIIU2 = df['recMII'].tolist()[1:]
    tmpList = [yNodesU1, yEdgesU1, yRecMIIU1, yNodesU2, yEdgesU2, yRecMIIU2]
    transList = [[row[i] for row in tmpList] for i in range(len(tmpList[0]))]   # transposition

    # generate a csv
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
    df.to_csv(csvPath)
 

def showFig9(figPath, nameBaselineS, namePertileS, nameIcedS):
    '''
    This is a func to read avg tile utilization from 6x6_*_*.csv and generate Parallel Bar Chart (Figure 9) in png.

    Parameters: path of figure, name of csv that stores Y-axis data

    Returns: NULL
    '''
    # read avg tile utilization of 6x6_unroll1/unroll2_baseline.csv
    nameBaselineS.index(fileBaselineU1) # to check if the file name is correct
    nameBaselineS.index(fileBaselineU2) # to check if the file name is correct
    df = pd.read_csv(fileBaselineU1)
    yBaselineU1 = df['avg tile utilization'].tolist()[1:]
    df = pd.read_csv(fileBaselineU2)
    yBaselineU2 = df['avg tile utilization'].tolist()[1:]
    # read avg tile utilization of 6x6_unroll1/unroll2_pertile.csv
    namePertileS.index(filePertileU1) # to check if the file name is correct
    namePertileS.index(filePertileU2) # to check if the file name is correct    
    df = pd.read_csv(filePertileU1)
    yPertileU1 = df['avg tile utilization'].tolist()[1:]
    df = pd.read_csv(filePertileU2)
    yPertileU2 = df['avg tile utilization'].tolist()[1:]
    # read avg tile utilization of 6x6_unroll1/unroll2_iced.csv
    nameIcedS.index(fileIcedU1) # to check if the file name is correct
    nameIcedS.index(fileIcedU2) # to check if the file name is correct     
    df = pd.read_csv(fileIcedU1)
    yIcedU1 = df['avg tile utilization'].tolist()[1:]
    df = pd.read_csv(fileIcedU2)
    yIcedU2 = df['avg tile utilization'].tolist()[1:]

    # draw a 6 bar chart
    plt.figure(figsize=(16, 5)) # the size of generated figure
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
    This is a func to read avg tile frequency from 6x6_*_*.csv and generate Parallel Bar Chart (Figure 10) in png.

    Parameters: path of figure, name of csv that stores Y-axis data

    Returns: NULL
    '''

    # read avg tile frequency of 6x6_unroll1/unroll2_baseline.csv  
    nameBaselineS.index(fileBaselineU1) # to check if the file name is correct
    nameBaselineS.index(fileBaselineU2) # to check if the file name is correct
    df = pd.read_csv(fileBaselineU1)
    yBaselineU1 = df['avg tile frequency'].tolist()[1:]
    df = pd.read_csv(fileBaselineU2)
    yBaselineU2 = df['avg tile frequency'].tolist()[1:]
    # read avg tile frequency of 6x6_unroll1/unroll2_pertile.csv    
    namePertileS.index(filePertileU1) # to check if the file name is correct
    namePertileS.index(filePertileU2) # to check if the file name is correct    
    df = pd.read_csv(filePertileU1)
    yPertileU1 = df['avg tile frequency'].tolist()[1:]
    df = pd.read_csv(filePertileU2)
    yPertileU2 = df['avg tile frequency'].tolist()[1:]
    # read avg tile frequency of 6x6_unroll1/unroll2_iced.csv
    nameIcedS.index(fileIcedU1) # to check if the file name is correct
    nameIcedS.index(fileIcedU2) # to check if the file name is correct     
    df = pd.read_csv(fileIcedU1)
    yIcedU1 = df['avg tile frequency'].tolist()[1:]
    df = pd.read_csv(fileIcedU2)
    yIcedU2 = df['avg tile frequency'].tolist()[1:]

    # draw a 6 bar chart
    plt.figure(figsize=(16, 5)) # the size of generated figure
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
    This is a func to caculate the energy from mappingII, number_of_idle_tiles and number_of_100/50/25/0_DVFS_tiles of 6x6_*_*.csv and generate Parallel Bar Chart (Figure 11) in png.

    Parameters: path of figure, name of csv that stores Y-axis data

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

    # read mappingII and number_of_idle_tiles of 6x6_unroll1/unroll2_baseline.csv
    nameBaselineS.index(fileBaselineU1) # to check if the file name is correct
    nameBaselineS.index(fileBaselineU2) # to check if the file name is correct
    df = pd.read_csv(fileBaselineU1)    
    number_of_idle_tiles_U1 = df['0% tiles u'].tolist()[1:] 
    mappingII_Baseline_U1 = df['mappingII'].tolist()[1:]
    df = pd.read_csv(fileBaselineU2)
    number_of_idle_tiles_U2 = df['0% tiles u'].tolist()[1:]
    mappingII_Baseline_U2 = df['mappingII'].tolist()[1:]
    # read mappingII and number_of_100/50/25/0_DVFS_tiles of 6x6_unroll1/unroll2_pertile.csv
    namePertileS.index(filePertileU1) # to check if the file name is correct
    namePertileS.index(filePertileU2) # to check if the file name is correct    
    df = pd.read_csv(filePertileU1)
    number_of_100_DVFS_tiles_Pertile_U1 = df['100% tiles f'].tolist()[1:]
    number_of_50_DVFS_tiles_Pertile_U1 = df['50% tiles f'].tolist()[1:]
    number_of_25_DVFS_tiles_Pertile_U1 = df['25% tiles f'].tolist()[1:]
    number_of_0_DVFS_tiles_Pertile_U1 = df['0% tiles f'].tolist()[1:]
    mappingII_Pertile_U1 = df['mappingII'].tolist()[1:]
    df = pd.read_csv(filePertileU2)
    number_of_100_DVFS_tiles_Pertile_U2 = df['100% tiles f'].tolist()[1:]
    number_of_50_DVFS_tiles_Pertile_U2 = df['50% tiles f'].tolist()[1:]
    number_of_25_DVFS_tiles_Pertile_U2 = df['25% tiles f'].tolist()[1:]
    number_of_0_DVFS_tiles_Pertile_U2 = df['0% tiles f'].tolist()[1:]
    mappingII_Pertile_U2 = df['mappingII'].tolist()[1:]
    # read mappingII and number_of_100/50/25_DVFS_tiles of 6x6_unroll1/unroll2_iced.csv
    nameIcedS.index(fileIcedU1) # to check if the file name is correct
    nameIcedS.index(fileIcedU2) # to check if the file name is correct 
    df = pd.read_csv(fileIcedU1)
    number_of_100_DVFS_tiles_Iced_U1 = df['100% tiles f'].tolist()[1:]
    number_of_50_DVFS_tiles_Iced_U1 = df['50% tiles f'].tolist()[1:]
    number_of_25_DVFS_tiles_Iced_U1 = df['25% tiles f'].tolist()[1:]
    mappingII_Iced_U1 = df['mappingII'].tolist()[1:]
    df = pd.read_csv(fileIcedU2)
    number_of_100_DVFS_tiles_Iced_U2 = df['100% tiles f'].tolist()[1:]
    number_of_50_DVFS_tiles_Iced_U2 = df['50% tiles f'].tolist()[1:]
    number_of_25_DVFS_tiles_Iced_U2 = df['25% tiles f'].tolist()[1:]
    mappingII_Iced_U2 = df['mappingII'].tolist()[1:]

    # find the minimal mappingII of baseline, pertile, iced
    minII_U1 = findMinII(mappingII_Baseline_U1, mappingII_Pertile_U1, mappingII_Iced_U1)
    minII_U2 = findMinII(mappingII_Baseline_U2, mappingII_Pertile_U2, mappingII_Iced_U2)

    # caculate corresponding power using the information above
    # Baseline: Power (36 tiles with SRAM) = 36 * (c * v100^2 * f100 + tile_static_power) + sram_power = 36 * 2.715 + 62.653 = 160.41. Energy = Power * (baselineII / minII).
    # Baseline: The v/f we use the 100% DVFS set and there is no control_overhead_DVFS for baseline.
    yBaselineU1 = [0] * testBenchsNum; yBaselineU2 = [0] * testBenchsNum;
    for i in range(testBenchsNum):
        if mappingII_Baseline_U1[i] == 0:
            yBaselineU1[i] = 0  # mappingII = 0 means mapping is failed, so the bar should be 0
        else:
            yBaselineU1[i] = (36 * (c * v100**2 * f100 + tile_static_power) + sram_power) * (mappingII_Baseline_U1[i] / minII_U1[i])
        if mappingII_Baseline_U2[i] == 0:
            yBaselineU2[i] = 0  # mappingII = 0 means mapping is failed, so the bar should be 0
        else:
            yBaselineU2[i] = (36 * (c * v100**2 * f100 + tile_static_power) + sram_power) * (mappingII_Baseline_U2[i] / minII_U2[i])

    # Baseline + Power-gating: Power = power_of_baseline - number_of_idle_tiles * (c * v100^2 * f100 + tile_static_power). The number_of_idle_tiles is number_of_0%_utilization_tiles.
    yBaselinePGU1 = [0] * testBenchsNum; yBaselinePGU2 = [0] * testBenchsNum
    for i in range(testBenchsNum):
        if mappingII_Baseline_U1[i] == 0:
            yBaselinePGU1[i] = 0  # mappingII = 0 means mapping is failed, so the bar should be 0
        else: 
            yBaselinePGU1[i] = ((yBaselineU1[i]) / (mappingII_Baseline_U1[i] / minII_U1[i]) - number_of_idle_tiles_U1[i] * (c * v100**2 * f100 + tile_static_power)) * (mappingII_Baseline_U1[i] / minII_U1[i])
        if mappingII_Baseline_U2[i] == 0:
            yBaselinePGU2[i] = 0  # mappingII = 0 means mapping is failed, so the bar should be 0
        else: 
            yBaselinePGU2[i] = ((yBaselineU2[i]) / (mappingII_Baseline_U2[i] / minII_U2[i]) - number_of_idle_tiles_U2[i] * (c * v100**2 * f100 + tile_static_power)) * (mappingII_Baseline_U2[i] / minII_U2[i])
    
    # Per-tile DVFS + Power-gating: Power = number_of_100%_DVFS_tiles * (c * v100^2 * f100) + number_of_50%_DVFS_tiles * (c * v50^2 * f50) + 
    # number_of_25%_DVFS_tiles * (c * v25^2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * (36 - number_of_0%_DVFS_tiles). Energy = Power * (pertileII / minII).
    yPertileU1 = [0] * testBenchsNum; yPertileU2 = [0] * testBenchsNum
    for i in range(testBenchsNum):
        if mappingII_Pertile_U1[i] == 0:
            yPertileU1[i] = 0  # mappingII = 0 means mapping is failed, so the bar should be 0
        else:
            yPertileU1[i] = (number_of_100_DVFS_tiles_Pertile_U1[i] * (c * v100**2 * f100) + number_of_50_DVFS_tiles_Pertile_U1[i] * (c * v50**2 * f50) + \
        number_of_25_DVFS_tiles_Pertile_U1[i] * (c * v25**2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * (36 - number_of_0_DVFS_tiles_Pertile_U1[i])) * (mappingII_Pertile_U1[i] / minII_U1[i])
        if mappingII_Pertile_U2[i] == 0:
            yPertileU2[i] = 0  # mappingII = 0 means mapping is failed, so the bar should be 0
        else:
            yPertileU2[i] = (number_of_100_DVFS_tiles_Pertile_U2[i] * (c * v100**2 * f100) + number_of_50_DVFS_tiles_Pertile_U2[i] * (c * v50**2 * f50) + \
        number_of_25_DVFS_tiles_Pertile_U2[i] * (c * v25**2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * (36 - number_of_0_DVFS_tiles_Pertile_U2[i])) * (mappingII_Pertile_U2[i] / minII_U2[i])

    # ICED: Power = number_of_100%_DVFS_tiles * (c * v100^2 * f100) + number_of_50%_DVFS_tiles * (c * v50^2 * f50) + 
    # number_of_25%_DVFS_tiles * (c * v25^2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * 9. Energy = Power * (icedII / minII).
    yIcedU1 = [0] * testBenchsNum; yIcedU2 = [0] * testBenchsNum
    for i in range(testBenchsNum):
        if mappingII_Iced_U1[i] == 0:
            yIcedU1[i] = 0  # mappingII = 0 means mapping is failed, so the bar should be 0
        else:
            yIcedU1[i] = (number_of_100_DVFS_tiles_Iced_U1[i] * (c * v100**2 * f100) + number_of_50_DVFS_tiles_Iced_U1[i] * (c * v50**2 * f50) + \
        number_of_25_DVFS_tiles_Iced_U1[i] * (c * v25**2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * 9) * (mappingII_Iced_U1[i] / minII_U1[i])
        if mappingII_Iced_U2[i] == 0:
            yIcedU2[i] = 0  # mappingII = 0 means mapping is failed, so the bar should be 0
        else:
            yIcedU2[i] = (number_of_100_DVFS_tiles_Iced_U2[i] * (c * v100**2 * f100) + number_of_50_DVFS_tiles_Iced_U2[i] * (c * v50**2 * f50) + \
        number_of_25_DVFS_tiles_Iced_U2[i] * (c * v25**2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * 9) * (mappingII_Iced_U2[i] / minII_U2[i])

    # draw a 8 bar chart
    plt.figure(figsize=(16, 5)) # the size of generated figure
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
    This is a func to read avg tile frequency from *_*_pertile/iced.csv and generate Parallel Bar Chart (Figure 12) in png.

    Parameters: path of figure, name of csv that stores Y-axis data

    Returns: NULL
    '''
    # read avg tile frequency of 2x2/4x4_unroll1_pertile.csv and 6x6/8x8_unroll1/unroll2_pertile.csv
    yPertile=[]
    for namePertile in namePertileS:
        df = pd.read_csv(namePertile)
        tmpList = df['avg tile frequency'].tolist()
        yPertile.extend(tmpList)
    # testBenchsNum is the length of a single yPertileX*U*
    yPertileX2U1 = yPertile[1:1+testBenchsNum]
    yPertileX4U1 = yPertile[2+testBenchsNum:2+2*testBenchsNum]
    yPertileX6U1 = yPertile[3+2*testBenchsNum:3+3*testBenchsNum]
    yPertileX6U2 = yPertile[4+3*testBenchsNum:4+4*testBenchsNum]
    yPertileX8U1 = yPertile[5+4*testBenchsNum:5+5*testBenchsNum]
    yPertileX8U2 = yPertile[6+5*testBenchsNum:6+6*testBenchsNum]
    # read avg tile frequency of 2x2/4x4_unroll1_iced.csv and 6x6/8x8_unroll1/unroll2_iced.csv
    yIced=[]
    for nameIced in nameIcedS:
        df = pd.read_csv(nameIced)
        tmpList = df['avg tile frequency'].tolist()
        yIced.extend(tmpList)
    # testBenchsNum is the length of a single yPertileX*U*
    yIcedX2U1 = yIced[1:1+testBenchsNum]
    yIcedX4U1 = yIced[2+testBenchsNum:2+2*testBenchsNum]
    yIcedX6U1 = yIced[3+2*testBenchsNum:3+3*testBenchsNum]
    yIcedX6U2 = yIced[4+3*testBenchsNum:4+4*testBenchsNum]
    yIcedX8U1 = yIced[5+4*testBenchsNum:5+5*testBenchsNum]
    yIcedX8U2 = yIced[6+5*testBenchsNum:6+6*testBenchsNum]

    # draw a 12 bar chart
    plt.figure(figsize=(16, 5)) # the size of generated figure
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
    testBenchs = ["fir.cpp", "latnrm.c", "fft.c", "dtw.cpp", "spmv.c", "conv.c", "relu.c", "histogram.cpp", "mvt.c", "gemm.c"]
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
#   main functions                                                          /
# ----------------------------------------------------------------------------

def mainBaseline(Rows, Columns, uFactor, doMapping = True):
    """
    This is a func to compile, run and map kernels under param_baseline.json.

    Parameters: rows and columns of the mapped CGRA, unrollFactor, doMapping (for showTableI())

    Returns: name of the csv that collects information of mapped kernels 
    """
    csvName = './tmp/t_' + str(Rows) + 'x' + str(Columns) + '_unroll' + str(uFactor) + '_baseline.csv'
    print("Generating", csvName)
    df = pd.DataFrame(dictCsv, index=[0])

    for kernel in testBenchs:
        if kernel == "NULL":
            dataS = [""]*dictColumn
            df.loc[len(df.index)] = dataS
            continue

        targetKernel = DVFSComp(kernel, uFactor)

        genBaselineJson = {
            "kernel": targetKernel,
            "targetFunction": False,
            "targetNested": False,
            "targetLoopsID": [0],
            "doCGRAMapping": doMapping,
            "row": Rows,
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
        if doMapping:
            DVFSMap(kernel, df)
        else:
            DVFSGen(kernel, df)

    df.to_csv(csvName)
    return csvName


def mainPertile(Rows, Columns, uFactor):
    """
    This is a func to compile, run and map kernels under param_pertile.json.

    Parameters: rows and columns of the mapped CGRA, unrollFactor

    Returns: name of the csv that collects information of mapped kernels 
    """
    csvName = './tmp/t_' + str(Rows) + 'x' + str(Columns) + '_unroll' + str(uFactor) + '_pertile.csv'
    print("Generating", csvName)
    df = pd.DataFrame(dictCsv, index=[0])

    for kernel in testBenchs:
        if kernel == "NULL":
            dataS = [""]*dictColumn
            df.loc[len(df.index)] = dataS
            continue

        targetKernel = DVFSComp(kernel, uFactor)

        genPertileJson = {
            "kernel": targetKernel,
            "targetFunction": False,
            "targetNested": False,
            "targetLoopsID": [0],
            "doCGRAMapping": True,
            "row": Rows,
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

        DVFSMap(kernel, df)

    df.to_csv(csvName)
    return csvName


def mainIced(Rows, Columns, uFactor):
    """
    This is a func to compile, run and map kernels under param_iced.json.

    Parameters: rows and columns of the mapped CGRA, unrollFactor

    Returns: name of the csv that collects information of mapped kernels 
    """
    csvName = './tmp/t_' + str(Rows) + 'x' + str(Columns) + '_unroll' + str(uFactor) + '_iced.csv'
    print("Generating", csvName)
    df = pd.DataFrame(dictCsv, index=[0])

    for kernel in testBenchs:
        if kernel == "NULL":
            dataS = [""]*dictColumn
            df.loc[len(df.index)] = dataS
            continue

        targetKernel = DVFSComp(kernel, uFactor)

        genIcedJson = {
            "kernel": targetKernel,
            "targetFunction": False,
            "targetNested": False,
            "targetLoopsID": [0],
            "doCGRAMapping": True,
            "row": Rows,
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

        DVFSMap(kernel, df)

    df.to_csv(csvName)
    return csvName


def main():
    """
    This is the main function that runs testBenchs with selected CGRA size and unrolling factor, then outputs result in png or in csv.

    Parameters: NULL

    Returns: NULL
    """
    print("ICEDdemo.py starts running.")
    timeStart = time.time()
    
    CGRAsizes = [6]  # the mapped CGRA size = 6
    unrollFactors = [2]   # unrolling factor = 1, 2
    nameCsvBaseline = []    
    csvPath = ""
    for CGRAsize in CGRAsizes:
        for unrollFactor in unrollFactors:      
            nameCsvBaseline.append(mainBaseline(CGRAsize, CGRAsize, unrollFactor, False)) 
    print("Generating Table I: Target workloads and streaming applications")
    csvPath = "./example/exampleTable.csv"
    showTableI(csvPath, nameCsvBaseline)

    print("Replace testBenchs to generate Fig. 9, 10, 11.")
    fig091011GenerationKernel()
    CGRAsizes = [6]  # the mapped CGRA size = 6
    unrollFactors = [1, 2]   # unrolling factor = 1, 2
    nameCsvBaseline = []    
    nameCsvPertile = []   
    nameCsvIced = []    
    figPath = ""
    for CGRAsize in CGRAsizes:
        for unrollFactor in unrollFactors:      
            nameCsvBaseline.append(mainBaseline(CGRAsize, CGRAsize, unrollFactor))
            nameCsvPertile.append(mainPertile(CGRAsize, CGRAsize, unrollFactor))
            nameCsvIced.append(mainIced(CGRAsize, CGRAsize, unrollFactor))  
    print("Generating Fig. 9: Average utilization of tiles across different kernels")
    figPath = "./example/exampleFig9.png"
    showFig9(figPath, nameCsvBaseline, nameCsvPertile, nameCsvIced)   

    print("Generating Fig. 10: Average DVFS level across different kernels")
    figPath = "./example/exampleFig10.png"
    showFig10(figPath, nameCsvBaseline, nameCsvPertile, nameCsvIced)   

    print("Generating Fig. 11: Evaluation of energy-efficiency")
    figPath = "./example/exampleFig11.png"
    nameCsvBaseline = ["./tmp/t_6x6_unroll1_baseline.csv", 
    "./tmp/t_6x6_unroll2_baseline.csv"]
    nameCsvPertile = ["./tmp/t_6x6_unroll1_pertile.csv", 
    "./tmp/t_6x6_unroll2_pertile.csv"]
    nameCsvIced = ["./tmp/t_6x6_unroll1_iced.csv", 
    "./tmp/t_6x6_unroll2_iced.csv"] 
    showFig11(figPath, nameCsvBaseline, nameCsvPertile, nameCsvIced)

    print("Replace testBenchs to generate Fig. 12.") 
    fig12GenerationKernel()
    CGRAsizes = [2, 4, 6, 8]  # the mapped CGRA size = 2, 4, 6, 8
    unrollFactors = [1, 2]   # unrolling factor = 1, 2
    nameCsvBaseline = []    
    nameCsvPertile = []   
    nameCsvIced = []    
    figPath = ""
    for CGRAsize in CGRAsizes:
        for unrollFactor in unrollFactors: 
            if (CGRAsize == 2 and unrollFactor == 2) or (CGRAsize == 4 and unrollFactor == 2):
                continue             
            nameCsvPertile.append(mainPertile(CGRAsize, CGRAsize, unrollFactor))
            nameCsvIced.append(mainIced(CGRAsize, CGRAsize, unrollFactor))     
    print("Generating Fig. 12: Evaluation of scalability") 
    figPath = "./example/exampleFig12.png"
    showFig12(figPath, nameCsvBaseline, nameCsvPertile, nameCsvIced)

    print("DONE. Time cost: ", time.time() - timeStart, "s")

# ----------------------------------------------------------------------------
#   run main                                                                /
# ----------------------------------------------------------------------------

main()
