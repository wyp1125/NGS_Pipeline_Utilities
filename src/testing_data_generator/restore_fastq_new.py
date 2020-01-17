import sys
import os
import collections

if len(sys.argv)<4:
    print("aligned_fastq(s) original_fastq(s) outdir")
    quit()

short_fqs=sys.argv[1].split(",")
origin_fqs=sys.argv[2].split(",")
print(short_fqs)
print(origin_fqs)

query_header=set()
for fq_file in short_fqs:
    lines=open(fq_file,"r")
    n=0
    for line in lines:
        if n%4==0:
            key=line.strip('\n').split("/")[0]
            query_header.add(key)
        n=n+1

for fq_file in origin_fqs:
    out_file=os.path.basename(fq_file)
    out_path=os.path.join(sys.argv[3],out_file)
    with open(fq_file,"r") as fl:
        with open(out_path,"w") as of:
            ct=0
            eachLine=fl.readline()
            while eachLine:
                if ct%4==0:
                    if ct>0:
                        if header in query_header:
                            of.write(content)
                    header = eachLine.strip('\n').split(" ")[0]
                    content=eachLine
                else:
                    content=content+eachLine
                eachLine=fl.readline()
                ct=ct+1
            if header in query_header:
                of.write(content)
    fl.close()

