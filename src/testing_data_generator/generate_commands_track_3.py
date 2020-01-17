import sys
import os
rundir=sys.argv[1]
bedpath=sys.argv[2]
outdir=sys.argv[3]
samtools=sys.argv[4]
bedtools=sys.argv[5]
fqtools=sys.argv[6]
bams=sys.argv[7:]
scripts_dir=os.path.join(outdir,"scripts")
i=0
for eachbam in bams:
    i+=1
    filepath=os.path.join(scripts_dir,"sub"+str(i)+".sh")
    with open(filepath,"w") as fl:
        bname=os.path.basename(eachbam)
        fname,ext=os.path.splitext(bname)
        cmd="#!/bin/bash"
        fl.write(cmd+'\n')
        cmd=samtools+" view -b -L "+bedpath+" "+eachbam+" >"+outdir+"/"+fname+".sel.bam"
        fl.write(cmd+'\n')
        if fqtools=="bedtools":
            cmd=bedtools+" bamtofastq -i "+outdir+"/"+fname+".sel.bam -fq "+outdir+"/"+fname+".fastq"
            fl.write(cmd+'\n')
        else:
            cmd=samtools+" bamshuf "+outdir+"/"+fname+".sel.bam "+outdir+"/"+fname+".sel.shuf"
            fl.write(cmd+'\n')
            cmd=samtools+" bam2fq "+outdir+"/"+fname+".sel.shuf.bam >"+outdir+"/"+fname+".fastq"
            fl.write(cmd+'\n')


