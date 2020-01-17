import os,sys
from optparse import OptionParser
import subprocess

def GetArgs():
    usage = "python cmp_single_file.py -t tested_run -f tested_file(relative) -r saved_output_folder -o output_dir"
    parser = OptionParser()
    parser.add_option("-t", "--testedRun", dest="tstRun", help="the path to the tested run")
    parser.add_option("-f", "--testedFile", dest="tstFile", help="the relative path to the tested file")
    parser.add_option("-r", "--reference", dest="refPath", help = "the saved output folder")
    parser.add_option("-o", "--outputDir", dest="outDir", help = "the output directory")
    (options, args) = parser.parse_args()
    tstRun = options.tstRun
    if not tstRun:
        print("No tested run specified.")
        print(usage)
        sys.exit(1)
    if not os.path.exists(tstRun):
        print("Tested run folder does not exist!")
        sys.exit(1)
    tstFile = options.tstFile
    if not tstFile:
        print("No tested file specified.")
        print(usage)
        sys.exit(1)
    refPath = options.refPath
    if not refPath:
        print("No saved output folder specified.")
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

    return (tstRun,tstFile,refPath,outDir)

def comp_file(refFile,testFile,outFolder):
    outcome="\t"
    code=0
    if os.path.isfile(testFile):
        outcome=outcome+"Tested file exists."
    else:
        outcome=outcome+"!!!Tested file does not exists."
        code=1
        return outcome,code
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
        code=1
    if os.path.splitext(refFile)[1] not in ['.zip','.gz','.tar','.bam','.bai']:
        tmpf1=os.path.join(outFolder,"temp1")
        tmpf2=os.path.join(outFolder,"temp2")
        os.system("sort "+refFile+" >"+tmpf1)
        os.system("sort "+testFile+" >"+tmpf2)
        cmd="diff "+tmpf1+" "+tmpf2
        P=subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out,err=P.communicate()
        if len(out)>0:
            outcome=outcome+"\n\t!!!Contents differ from the reference."
            code=1
        else:
            outcome=outcome+"\n\tContents are the same as the reference."
    return outcome,code

if __name__=="__main__":
    tstRun,tstFile,refPath,outDir=GetArgs()
    resFile=os.path.join(outDir,"regr.outcome")
    with open(resFile,'w') as of:
        saved_path=os.path.join(refPath,tstFile)
        test_path=os.path.join(tstRun,tstFile)
        if os.path.isfile(saved_path)==False:
            code=1
            print(code)
            print("The tested file does not have a corresponding reference!")
        else:
            outcome,code=comp_file(saved_path,test_path,outDir)
            print(code)
            print("Tested file: "+test_path)
            print("Reference file: "+saved_path)
            of.write("Tested file: {}\nReference file: {}\n".format(test_path,saved_path))
            print(outcome)
            of.write(outcome+"\n")

