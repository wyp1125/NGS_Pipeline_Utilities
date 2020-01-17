import sys
import os
import re
aligner=sys.argv[1]
aligner_path=sys.argv[2]
index=sys.argv[3]
rundir=sys.argv[4]
bedpath=sys.argv[5]
outdir=sys.argv[6]
mode=sys.argv[7]
samtools=sys.argv[8]
bedtools=sys.argv[9]
fqtool=sys.argv[10]
python=sys.argv[11]
python_lib=sys.argv[12]
res_script=sys.argv[13]
cfg_file=sys.argv[14]
threads=sys.argv[15]
sentieon=sys.argv[16]
pythonhome=sys.argv[17]
fastqs_full=sys.argv[18:]

def get_pairs(x):
    p1=[]
    p2=[]
    for f in x:
        if re.search("_R2_",f)!=None:
            p2.append(f)
        else:
            p1.append(f)
    y=p1
    if len(p2)>0:
        sole_R2=[]
        for f2 in p2:
            temp=f2.replace("_R2_","_R1_")
            paired=0
            i=0
            for f1 in p1:
                if f1==temp:
                    y[i]=y[i]+","+f2
                    paired=1
                    break
                i+=1
            if paired==0:
                sole_R2.append(f2)
    return y+sole_R2

fastqs_base=[]
for path in fastqs_full:
    fastqs_base.append(os.path.basename(path))

paired_fastqs=get_pairs(fastqs_base)
print(paired_fastqs)
scripts_dir=os.path.join(outdir,"scripts")
for i in range(0,len(paired_fastqs)):
    filepath=os.path.join(scripts_dir,"sub"+str(i+1)+".sh")
    splitfile=paired_fastqs[i].split(",")
    nfile=len(splitfile)
    with open(filepath,"w") as fl:
        cmd="#!/bin/bash"
        fl.write(cmd+'\n')
        if mode=='1':
            if aligner=="bwa":
                fl.write("source "+cfg_file+'\n')
                if nfile==2:
                    sample=splitfile[0].split("_R1")[0]
                    cmd=aligner_path+" mem -t "+threads+" -R \"@RG\\tID:aln"+str(i+1)+"\\tSM:"+sample+"\\tPL:Illumina\" "+index+" "+rundir+"/"+splitfile[0]+" "+rundir+"/"+splitfile[1]+" >"+rundir+"/aln"+str(i+1)+".sam"
                else:
                    sample=splitfile[0].split(".fastq")[0]
                    cmd=aligner_path+" mem -t "+threads+" -R \"@RG\\tID:aln"+str(i+1)+"\\tSM:"+sample+"\\tPL:Illumina\" "+index+" "+rundir+"/"+splitfile[0]+" >"+rundir+"/aln"+str(i+1)+".sam"
            else:
                if nfile==2:
                    cmd=aligner_path+" -S "+index+" -1 "+rundir+"/"+splitfile[0]+" -2 "+rundir+"/"+splitfile[1]+" >"+rundir+"/aln"+str(i+1)+".sam"
                else:
                    cmd=aligner_path+" -S "+index+" "+rundir+"/"+splitfile[0]+" >"+rundir+"/aln"+str(i+1)+".sam"
            fl.write(cmd+'\n')
            #cmd=samtools+" view -bS "+rundir+"/aln"+str(i+1)+".sam |"+samtools+" sort - "+rundir+"/aln"+str(i+1)
            cmd=sentieon+"/bin/sentieon util sort -t "+threads+" --sam2bam -i "+rundir+"/aln"+str(i+1)+".sam -o "+rundir+"/aln"+str(i+1)+".bam"
            fl.write(cmd+'\n')
            #cmd=samtools+" index "+rundir+"/aln"+str(i+1)+".bam"
            #fl.write(cmd+'\n')
        cmd=samtools+" view -b -L "+bedpath+" "+rundir+"/aln"+str(i+1)+".bam >"+outdir+"/aln"+str(i+1)+".sel.bam"
        fl.write(cmd+'\n')
        if fqtool=="bedtools":
            cmd=bedtools+" bamtofastq -i "+outdir+"/aln"+str(i+1)+".sel.bam -fq "+outdir+"/aln"+str(i+1)+".raw.fastq"
            fl.write(cmd+'\n')
        else:
            cmd=samtools+" bamshuf "+outdir+"/aln"+str(i+1)+".sel.bam "+outdir+"/aln"+str(i+1)+".sel.shuf"
            fl.write(cmd+'\n')
            cmd=samtools+" bam2fq "+outdir+"/aln"+str(i+1)+".sel.shuf.bam >"+outdir+"/aln"+str(i+1)+".raw.fastq"
            fl.write(cmd+'\n')
        cmd="export LD_LIBRARY_PATH="+python_lib
        fl.write(cmd+'\n')
        cmd="export PYTHONHOME="+pythonhome
        fl.write(cmd+'\n')
        if nfile==2:
            cmd=python+" "+res_script+" "+outdir+"/aln"+str(i+1)+".raw.fastq "+rundir+"/"+splitfile[0]+","+rundir+"/"+splitfile[1]+" "+outdir
        else:
            cmd=python+" "+res_script+" "+outdir+"/aln"+str(i+1)+".raw.fastq "+rundir+"/"+splitfile[0]+" "+outdir
        fl.write(cmd+'\n')

