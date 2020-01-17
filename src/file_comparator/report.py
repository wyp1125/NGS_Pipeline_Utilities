import os,sys
from optparse import OptionParser
import subprocess

def GetArgs():
    usage = "python report.py -c checkpoint_file -g goldendata_running_folder -r saved_output_folder -o out_directory -s start_point -e end_point"
    parser = OptionParser()
    parser.add_option("-c", "--checkpointFile", dest="chkFile", help = "the checkpoint file")
    parser.add_option("-g", "--goldenrun", dest="gldPath", help="the sample folder of goldendata after running with debug mode")
    parser.add_option("-r", "--reference", dest="refPath", help = "the saved_output_folder")
    parser.add_option("-o", "--outputDir", dest="outDir", help = "the output directory")
    parser.add_option("-s", "--startPoint", dest="staPoint", help = "the start step in the checkpoint file")
    parser.add_option("-e", "--endPoint", dest="endPoint", help = "the end step in the checkpoint file")
    (options, args) = parser.parse_args()
    chkFile = options.chkFile
    if not chkFile:
        print("No checkpoint file specified.")
        print(usage)
        sys.exit(1)
    outDir = options.outDir
    if not outDir:
        print("No output directory specified.")
        print(usage)
        sys.exit(1)
    if not os.path.exists(outDir):
        try: 
            os.makedirs(outDir)
        except:
            print("Cannot make the output dir!")
            sys.exit(1)
    #resFile = os.path.join(outDir,"cmp_outcome.txt")
    gldPath = options.gldPath
    if not gldPath:
        print("No golden data running specified.")
        print(usage)
        sys.exit(1)
    refPath = options.refPath
    if not refPath:
        print("No saved output folder specified.")
        print(usage)
        sys.exit(1)
    temp1 = options.staPoint
    if not temp1:
        print("No start point specified.")
        print(usage)
        sys.exit(1)
    staPoint=int(temp1)
    temp2 = options.endPoint
    if not temp2:
        print("No end point specified.")
        print(usage)
        sys.exit(1)
    endPoint=int(temp2)
    return (chkFile,outDir,gldPath,refPath,staPoint,endPoint)

def comp_file(refFile,testFile,outFolder):
    outcome="\t"
    if os.path.isfile(testFile):
        outcome=outcome+"Tested file exists."
    else:
        outcome=outcome+"!!!Tested file does not exists."
        return outcome
    fz1=os.path.getsize(refFile)
    fz2=os.path.getsize(testFile)
    if fz1==fz2:
        outcome=outcome+"\n\tFile size 100% matches with reference."
    else:
        x=float(fz2-fz1)/float(fz1)
        if x>0:
            outcome=outcome+"\n\t!!!File size increases by {:.2%}.".format(x)
        else:
            outcome=outcome+"\n\t!!!File size decreases by {:.2%}.".format(-x)
    if os.path.splitext(refFile)[1] not in ['.tar','.zip','.gz','.bam','.bai']:
        tmpf1=os.path.join(outFolder,"temp1")
        tmpf2=os.path.join(outFolder,"temp2")
        os.system("sort "+refFile+" >"+tmpf1)
        os.system("sort "+testFile+" >"+tmpf2)
        cmd="diff "+tmpf1+" "+tmpf2
        P=subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out,err=P.communicate()
        #print(out)
        if len(out)>0:
            outcome=outcome+"\n\t!!!Contents differ from the reference."
        else:
            outcome=outcome+"\n\tContents are the same as the reference."
    return outcome

if __name__=="__main__":
    chkFile,outDir,gldPath,refPath,staPoint,endPoint=GetArgs()
    checkpoint_file=chkFile
    if os.path.isfile(os.path.abspath(checkpoint_file)) == False:
        print("The checkpoint file cannot be found. Please notify the golden data author.")
        sys.exit(1)
    dat=open(checkpoint_file,'r')
    stepid=[]
    stage=[]
    step=[]
    scripts=[]
    folder=[]
    fname=[]
    for line in dat:
        word=line.strip("\n").split('\t')
        stepid.append(int(word[0]))
        stage.append(word[1])
        step.append(word[2])
        scripts.append(word[3])
        folder.append(word[4])
        fname.append(word[5])
    n=len(step)
    resFile=os.path.join(outDir,"regr.outcome")
    with open(resFile,'w') as of:
        for i in range(n):
            if stepid[i]>=staPoint and stepid[i]<=endPoint:
                relative_path=folder[i]+"/"+fname[i]
                if folder[i]=="./":
                    relative_path=fname[i]
                saved_path=refPath+"/"+relative_path
                test_path=gldPath+"/"+relative_path
                print(test_path)
                print(saved_path)
                if os.path.isfile(saved_path)==False:
                    print("Saved output was corrupt. Please notify the golden data author")
                else:
                    print("Step {}: - STAGE: {}; FUNC: {}\n\tTESTED FILE: {}".format(stepid[i],stage[i],step[i],relative_path))
                    of.write("Step {}: - STAGE: {}; FUNC: {}\n\tTESTED FILE: {}\n".format(stepid[i],stage[i],step[i],relative_path))
                    outcome=comp_file(saved_path,test_path,outDir)
                    print(outcome)
                    of.write(outcome+"\n")
