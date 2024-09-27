# ----------------------------------------------------------------------------
#   Filename: testT3forDVFS.py                                              /
#   Description: script of ICED                                       /
#   Author: Miaomiao Jiang, strat from 2023-10-16                           /
# ----------------------------------------------------------------------------

import os
import subprocess
import json
import time        # for time out
import eventlet    # for time out
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ----------------------------------------------------------------------------
#   global variables in testT3forDVFS.py                                    /
# ----------------------------------------------------------------------------

testBenchs = ["fir.cpp", "conv.c", "histogram.cpp"]
dictCvs = {'kernels': "", 'DFG nodes': "", 'DFG edges': "", 'recMII': "", 'avg tile utilization': "", '0% tiles u': "", 'avg tile frequency': "",	'0% tiles f': "", 
'25% tiles f': "",'50% tiles f': "", '100% tiles f': ""}  # column names of generated CVS
dictColumn = 11
jsonName = "./paramDVFS.json"   # name of generated json file
timeOutSet = 1500   # set Timeout = 25 minutes
# For your convience, the names of cvs are listed to avoid wating for the cvs generation in main function.
# nameCvsBaseline = ["./tmp/t_2x2_unroll1_baseline.csv", "./tmp/t_2x2_unroll2_baseline.csv", "./tmp/t_4x4_unroll1_baseline.csv", "./tmp/t_4x4_unroll2_baseline.csv",
#  "./tmp/t_6x6_unroll1_baseline.csv", "./tmp/t_6x6_unroll2_baseline.csv", "./tmp/t_8x8_unroll1_baseline.csv", "./tmp/t_8x8_unroll2_baseline.csv"]
# nameCvsPertile = ["./tmp/t_2x2_unroll1_pertile.csv", "./tmp/t_2x2_unroll2_pertile.csv", "./tmp/t_4x4_unroll1_pertile.csv", "./tmp/t_4x4_unroll2_pertile.csv",
#  "./tmp/t_6x6_unroll1_pertile.csv", "./tmp/t_6x6_unroll2_pertile.csv", "./tmp/t_8x8_unroll1_pertile.csv", "./tmp/t_8x8_unroll2_pertile.csv"]
# nameCvsIced = ["./tmp/t_2x2_unroll1_proposed.csv", "./tmp/t_2x2_unroll2_proposed.csv", "./tmp/t_4x4_unroll1_proposed.csv", "./tmp/t_4x4_unroll2_proposed.csv",
#  "./tmp/t_6x6_unroll1_proposed.csv", "./tmp/t_6x6_unroll2_proposed.csv", "./tmp/t_8x8_unroll1_proposed.csv", "./tmp/t_8x8_unroll2_proposed.csv"]

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
    uCommand4 = "clang-12 -emit-llvm -funroll-loops -mllvm -unroll-count=4 -O3 -o kernel.bc -c "    # unroll = 4
    appCommand0 = "./kernels/"
    generalCommand = fileSource + "/" + fileName
    compileCommand = ""

    if uFactor == 1:
        compileCommand = uCommand0 + appCommand0 + generalCommand
    elif uFactor == 2:
        compileCommand = uCommand2 + appCommand0 + generalCommand
    elif uFactor == 4:
        compileCommand = uCommand4 + appCommand0 + generalCommand

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
        print("Time Out!")

    df.loc[len(df.index)] = dataS


def showTableI(cvsPath, nameBaselineS):
    '''
    This is a func to generate information of kernels in cvs.

    Parameters: path of cvs, information of kernels in baseline

    Returns: NULL
    '''

    # read nodes, edges, and RecMII of 6x6_unroll1/unroll2_baseline
    df = pd.read_csv(nameBaselineS[4])
    yNodesU1 = df['DFG nodes'].tolist()
    yNodesU1 = yNodesU1[1:]
    df = pd.read_csv(nameBaselineS[5])
    yNodesU2 = df['DFG nodes'].tolist()
    yNodesU2 = yNodesU2[1:]
    df = pd.read_csv(nameBaselineS[4])
    yEdgesU1 = df['DFG edges'].tolist()
    yEdgesU1 = yEdgesU1[1:]
    df = pd.read_csv(nameBaselineS[5])
    yEdgesU2 = df['DFG edges'].tolist()
    yEdgesU2 = yEdgesU2[1:]
    df = pd.read_csv(nameBaselineS[4])
    yRecMIIU1 = df['recMII'].tolist()
    yRecMIIU1 = yRecMIIU1[1:]
    df = pd.read_csv(nameBaselineS[5])
    yRecMIIU2 = df['recMII'].tolist()
    yRecMIIU2 = yRecMIIU2[1:]
    tmpList = [yNodesU1, yEdgesU1, yRecMIIU1, yNodesU2, yEdgesU2, yRecMIIU2]
    transList = [[row[i] for row in tmpList] for i in range(len(tmpList[0]))]   # transposition

    # generate a cvs
    tableIDict = {'Kernel': "", 'Unroll1 Nodes': "", 'Unroll1 Edges': "", 'Unroll1 RecMII': "", 'Unroll2 Nodes': "", 'Unroll2 Edges': "", 'Unroll2 RecMII': ""}
    tableIDictColumn = 7
    df = pd.DataFrame(tableIDict, index=[0])
    Bench1 = []; Bench2= []; Bench3 = []
    Bench1.append(testBenchs[0])    # fir.cpp
    Bench2.append(testBenchs[1])    # conv.c
    Bench3.append(testBenchs[2])    # histogram.cpp
    Bench1 = Bench1 + transList[0]
    Bench2 = Bench2 + transList[1]
    Bench3 = Bench3 + transList[2]
    df.loc[len(df.index)] = Bench1
    df.loc[len(df.index)] = Bench2
    df.loc[len(df.index)] = Bench3
    df.to_csv(cvsPath)
 

def showFig9(figPath, nameBaselineS, namePertileS, nameIcedS):
    '''
    This is a func to generate Parallel Bar Chart (Figure 9) in png.

    Parameters: path of figure, Y-axis data

    Returns: NULL
    '''
    # read avg tile utilization of 6x6_unroll1/unroll2_baseline
    df = pd.read_csv(nameBaselineS[4])
    yBaselineU1 = df['avg tile utilization'].tolist()
    yBaselineU1 = yBaselineU1[1:]
    df = pd.read_csv(nameBaselineS[5])
    yBaselineU2 = df['avg tile utilization'].tolist()
    yBaselineU2 = yBaselineU2[1:]
    # read avg tile utilization of 6x6_unroll1/unroll2_pertile
    df = pd.read_csv(namePertileS[4])
    yPertileU1 = df['avg tile utilization'].tolist()
    yPertileU1 = yPertileU1[1:]
    df = pd.read_csv(namePertileS[5])
    yPertileU2 = df['avg tile utilization'].tolist()
    yPertileU2 = yPertileU2[1:]
    # read avg tile utilization of 6x6_unroll1/unroll2_iced
    df = pd.read_csv(nameIcedS[4])
    yIcedU1 = df['avg tile utilization'].tolist()
    yIcedU1 = yIcedU1[1:]
    df = pd.read_csv(nameIcedS[5])
    yIcedU2 = df['avg tile utilization'].tolist()
    yIcedU2 = yIcedU2[1:]

    # draw a 6 bar chart
    plt.figure(figsize=(10, 5))
    plt.subplot(132)
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
    plt.legend(loc=2, bbox_to_anchor=(1.05,1.0),borderaxespad = 0.) # put legend outside the box
    plt.savefig(figPath)


def showFig10(figPath, nameBaselineS, namePertileS, nameIcedS):
    '''
    This is a func to generate Parallel Bar Chart (Figure 10) in png.

    Parameters: path of figure, Y-axis data

    Returns: NULL
    '''

    # read avg tile frequency of 6x6_unroll1/unroll2_baseline
    df = pd.read_csv(nameBaselineS[4])
    yBaselineU1 = df['avg tile frequency'].tolist()
    yBaselineU1 = yBaselineU1[1:]
    df = pd.read_csv(nameBaselineS[5])
    yBaselineU2 = df['avg tile frequency'].tolist()
    yBaselineU2 = yBaselineU2[1:]
    # read avg tile frequency of 6x6_unroll1/unroll2_pertile
    df = pd.read_csv(namePertileS[4])
    yPertileU1 = df['avg tile frequency'].tolist()
    yPertileU1 = yPertileU1[1:]
    df = pd.read_csv(namePertileS[5])
    yPertileU2 = df['avg tile frequency'].tolist()
    yPertileU2 = yPertileU2[1:]
    # read avg tile frequency of 6x6_unroll1/unroll2_iced
    df = pd.read_csv(nameIcedS[4])
    yIcedU1 = df['avg tile frequency'].tolist()
    yIcedU1 = yIcedU1[1:]
    df = pd.read_csv(nameIcedS[5])
    yIcedU2 = df['avg tile frequency'].tolist()
    yIcedU2 = yIcedU2[1:]

    # draw a 6 bar chart
    plt.figure(figsize=(10, 5))
    plt.subplot(132)
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
    plt.legend(loc=2, bbox_to_anchor=(1.05,1.0),borderaxespad = 0.) # put legend outside the box
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
    df = pd.read_csv(nameBaselineS[4])
    number_of_idle_tiles_U1 = df['0% tiles u'].tolist()
    number_of_idle_tiles_U1 = number_of_idle_tiles_U1[1:]
    df = pd.read_csv(nameBaselineS[5])
    number_of_idle_tiles_U2 = df['0% tiles u'].tolist()
    number_of_idle_tiles_U2 = number_of_idle_tiles_U2[1:]
    # read number_of_100/50/25/0_DVFS_tiles of 6x6_unroll1/unroll2_pertile
    df = pd.read_csv(namePertileS[4])
    number_of_100_DVFS_tiles_Pertile_U1 = df['100% tiles f'].tolist()
    number_of_100_DVFS_tiles_Pertile_U1 = number_of_100_DVFS_tiles_Pertile_U1[1:]
    df = pd.read_csv(namePertileS[5])
    number_of_100_DVFS_tiles_Pertile_U2 = df['100% tiles f'].tolist()
    number_of_100_DVFS_tiles_Pertile_U2 = number_of_100_DVFS_tiles_Pertile_U2[1:]
    df = pd.read_csv(namePertileS[4])
    number_of_50_DVFS_tiles_Pertile_U1 = df['50% tiles f'].tolist()
    number_of_50_DVFS_tiles_Pertile_U1 = number_of_50_DVFS_tiles_Pertile_U1[1:]
    df = pd.read_csv(namePertileS[5])
    number_of_50_DVFS_tiles_Pertile_U2 = df['50% tiles f'].tolist()
    number_of_50_DVFS_tiles_Pertile_U2 = number_of_50_DVFS_tiles_Pertile_U2[1:]
    df = pd.read_csv(namePertileS[4])
    number_of_25_DVFS_tiles_Pertile_U1 = df['25% tiles f'].tolist()
    number_of_25_DVFS_tiles_Pertile_U1 = number_of_25_DVFS_tiles_Pertile_U1[1:]
    df = pd.read_csv(namePertileS[5])
    number_of_25_DVFS_tiles_Pertile_U2 = df['25% tiles f'].tolist()
    number_of_25_DVFS_tiles_Pertile_U2 = number_of_25_DVFS_tiles_Pertile_U2[1:]
    df = pd.read_csv(namePertileS[4])
    number_of_0_DVFS_tiles_Pertile_U1 = df['0% tiles f'].tolist()
    number_of_0_DVFS_tiles_Pertile_U1 = number_of_0_DVFS_tiles_Pertile_U1[1:]
    df = pd.read_csv(namePertileS[5])
    number_of_0_DVFS_tiles_Pertile_U2 = df['0% tiles f'].tolist()
    number_of_0_DVFS_tiles_Pertile_U2 = number_of_0_DVFS_tiles_Pertile_U2[1:]
    # read number_of_100/50/25_DVFS_tiles of 6x6_unroll1/unroll2_iced
    df = pd.read_csv(nameIcedS[4])
    number_of_100_DVFS_tiles_Iced_U1 = df['100% tiles f'].tolist()
    number_of_100_DVFS_tiles_Iced_U1 = number_of_100_DVFS_tiles_Iced_U1[1:]
    df = pd.read_csv(nameIcedS[5])
    number_of_100_DVFS_tiles_Iced_U2 = df['100% tiles f'].tolist()
    number_of_100_DVFS_tiles_Iced_U2 = number_of_100_DVFS_tiles_Iced_U2[1:]
    df = pd.read_csv(nameIcedS[4])
    number_of_50_DVFS_tiles_Iced_U1 = df['50% tiles f'].tolist()
    number_of_50_DVFS_tiles_Iced_U1 = number_of_50_DVFS_tiles_Iced_U1[1:]
    df = pd.read_csv(nameIcedS[5])
    number_of_50_DVFS_tiles_Iced_U2 = df['50% tiles f'].tolist()
    number_of_50_DVFS_tiles_Iced_U2 = number_of_50_DVFS_tiles_Iced_U2[1:]
    df = pd.read_csv(nameIcedS[4])
    number_of_25_DVFS_tiles_Iced_U1 = df['25% tiles f'].tolist()
    number_of_25_DVFS_tiles_Iced_U1 = number_of_25_DVFS_tiles_Iced_U1[1:]
    df = pd.read_csv(nameIcedS[5])
    number_of_25_DVFS_tiles_Iced_U2 = df['25% tiles f'].tolist()
    number_of_25_DVFS_tiles_Iced_U2 = number_of_25_DVFS_tiles_Iced_U2[1:]


    # caculate corresponding power using the information above
    # Baseline: Power (36 tiles with SRAM) = 36 * (c * v100^2 * f100 + tile_static_power) + 62.653 = 36 * 2.715 + 62.653 = 160.41. 
    # Baseline: The v/f we use the 100% DVFS set and there is no control_overhead_DVFS for baseline.
    yBaselineU1 = [36 * (c * v100**2 * f100 + tile_static_power) + sram_power]*3
    yBaselineU2 = [36 * (c * v100**2 * f100 + tile_static_power) + sram_power]*3
    # Baseline + Power-gating: Power = power_of_baseline - number_of_idle_tiles * (c * v100^2 * f100 + tile_static_power). The number_of_idle_tiles is number_of_0%_utilization_tiles.
    yBaselinePGU1 = [0]*3; yBaselinePGU2 = [0]*3
    for i in range(3):
        yBaselinePGU1[i] = yBaselineU1[i] - number_of_idle_tiles_U1[i] * (c * v100**2 * f100 + tile_static_power)
        yBaselinePGU2[i] = yBaselineU2[i] - number_of_idle_tiles_U2[i] * (c * v100**2 * f100 + tile_static_power)
    # Per-tile DVFS + Power-gating: Power = number_of_100%_DVFS_tiles * (c * v100^2 * f100) + number_of_50%_DVFS_tiles * (c * v50^2 * f50) + 
    # number_of_25%_DVFS_tiles * (c * v25^2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * (36 - number_of_0%_DVFS_tiles).
    yPertileU1 = [0]*3; yPertileU2 = [0]*3
    for i in range(3):
        yPertileU1[i] = number_of_100_DVFS_tiles_Pertile_U1[i] * (c * v100**2 * f100) + number_of_50_DVFS_tiles_Pertile_U1[i] * (c * v50**2 * f50) + \
        number_of_25_DVFS_tiles_Pertile_U1[i] * (c * v25**2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * (36 - number_of_0_DVFS_tiles_Pertile_U1[i])
        yPertileU2[i] = number_of_100_DVFS_tiles_Pertile_U2[i] * (c * v100**2 * f100) + number_of_50_DVFS_tiles_Pertile_U2[i] * (c * v50**2 * f50) + \
        number_of_25_DVFS_tiles_Pertile_U2[i] * (c * v25**2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * (36 - number_of_0_DVFS_tiles_Pertile_U2[i])

    print(number_of_0_DVFS_tiles_Pertile_U1)
    # ICED: Power = number_of_100%_DVFS_tiles * (c * v100^2 * f100) + number_of_50%_DVFS_tiles * (c * v50^2 * f50) + 
    # number_of_25%_DVFS_tiles * (c * v25^2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * 9.
    yIcedU1 = [0]*3; yIcedU2 = [0]*3
    for i in range(3):
        yIcedU1 = number_of_100_DVFS_tiles_Iced_U1[i] * (c * v100**2 * f100) + number_of_50_DVFS_tiles_Iced_U1[i] * (c * v50**2 * f50) + \
        number_of_25_DVFS_tiles_Iced_U1[i] * (c * v25**2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * 9
        yIcedU2 = number_of_100_DVFS_tiles_Iced_U2[i] * (c * v100**2 * f100) + number_of_50_DVFS_tiles_Iced_U2[i] * (c * v50**2 * f50) + \
        number_of_25_DVFS_tiles_Iced_U2[i] * (c * v25**2 * f25) + 36 * tile_static_power + sram_power + control_overhead_DVFS * 9

    # draw a 8 bar chart
    plt.figure(figsize=(12, 5))
    plt.subplot(132)
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
    plt.legend(loc=2, bbox_to_anchor=(1.05,1.0),borderaxespad = 0.) # put legend outside the box
    plt.savefig(figPath)


def showFig12(figPath, nameBaselineS, namePertileS, nameIcedS):
    '''
    This is a func to caculate the power from given information and generate Parallel Bar Chart (Figure 12) in png.

    Parameters: path of figure, Y-axis data

    Returns: NULL
    '''
    # read avg tile frequency of 2x2/4x4/6x6/8x8_unroll1/unroll2_pertile
    yPertile=[]
    for namePertile in namePertileS:
        df = pd.read_csv(namePertile)
        tmpList = df['avg tile frequency'].tolist()
        yPertile.extend(tmpList)
    yPertileX2U1 = yPertile[1:4]
    yPertileX4U1 = yPertile[9:12]
    yPertileX6U1 = yPertile[17:20]
    yPertileX6U2 = yPertile[21:24]
    yPertileX8U1 = yPertile[25:28]
    yPertileX8U2 = yPertile[29:32]
    # read avg tile frequency of 2x2/4x4/6x6/8x8_unroll1/unroll2_iced
    yIced=[]
    for nameIced in nameIcedS:
        df = pd.read_csv(nameIced)
        tmpList = df['avg tile frequency'].tolist()
        yIced.extend(tmpList)
    yIcedX2U1 = yIced[1:4]
    yIcedX4U1 = yIced[9:12]
    yIcedX6U1 = yIced[17:20]
    yIcedX6U2 = yIced[21:24]
    yIcedX8U1 = yIced[25:28]
    yIcedX8U2 = yIced[29:32]

    # draw a 12 bar chart
    plt.figure(figsize=(14, 5))
    plt.subplot(132)
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
    plt.legend(loc=2, bbox_to_anchor=(1.05,1.0),borderaxespad = 0.) # put legend outside the box
    plt.savefig(figPath)

# ----------------------------------------------------------------------------
#   main function in testT3forDVFS.py                                       /
# ----------------------------------------------------------------------------

def mainBaseline(Crows, Columns, uFactor):
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
            "bypassConstraint": 4,
            "isStaticElasticCGRA": False,
            "ctrlMemConstraint": 10,
            "regConstraint": 8,
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
            "bypassConstraint": 4,
            "isStaticElasticCGRA": False,
            "ctrlMemConstraint": 10,
            "regConstraint": 8,
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
            "bypassConstraint": 4,
            "isStaticElasticCGRA": False,
            "ctrlMemConstraint": 10,
            "regConstraint": 8,
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

    CGRAsizes = [2, 4, 6, 8]  # the mapped CGRA size = 2, 4, 6, 8
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

    print("Generating Table I: Target workloads and streaming applications")
    figPath = "./example/exampleTable.cvs"
    showTableI(figPath, nameCvsBaseline)

    print("Generating Fig. 9: Average utilization of tiles across different kernels")
    figPath = "./example/exampleFig9.png"
    showFig9(figPath, nameCvsBaseline, nameCvsPertile, nameCvsIced)   

    print("Generating Fig. 10: Average DVFS level across different kernels")
    figPath = "./example/exampleFig10.png"
    showFig10(figPath, nameCvsBaseline, nameCvsPertile, nameCvsIced)   

    print("Generating Fig. 11: Evaluation of energy-efficiency")
    figPath = "./example/exampleFig11.png"
    showFig11(figPath, nameCvsBaseline, nameCvsPertile, nameCvsIced)

    print("Generating Fig. 12: Evaluation of scalability") 
    figPath = "./example/exampleFig12.png"
    showFig12(figPath, nameCvsBaseline, nameCvsPertile, nameCvsIced)

    print("DONE.")

# ----------------------------------------------------------------------------
#   run main in testT3forDVFS.py                                            /
# ----------------------------------------------------------------------------

main()
