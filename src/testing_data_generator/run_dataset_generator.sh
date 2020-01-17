#!/bin/bash

##################################################
#Usage
##################################################

read -r -d '' DOCS <<DOCS
run_dataset_generator.sh usage: $0 options

This script takes in a directory of fastq files and a bed file containing selected chromosomal regions, and compute the reads that can be aligned to the selected chromsomal regions in fastq format.

The output files will have the same file names with the input fastq files. Thus,the output directory must be different from the input directory.

Ideally, the selected chromsomal regions will contain known genetic alteratoins such as SNPs, gene fusions, CNVs or SVs. Thus, the output fastq files can be used as golden datasets for rapidly developing or testing clinical pipelines.

OPTIONS:
    -h                [optional]  help, Show this message
    -i <path>         [required]  input directory which should contain fastq files and/or bam files      
    -a                [optional]  should be "bwa" (default) or "bowtie"
    -s                [optional]  should be "bedtools" (default) or "samtools"
    -b                [required]  path to the bed file
    -o                [required]  output (except the entire alignment) 

DOCS

echo "***** Beginning the goldendata generator pipeline *****"

if [[ -z ${GDG_PROFILE} ]]; then
    SCRIPT=$( readlink -m $( type -p $0 ))
    SCRIPT_DIR=$(dirname ${SCRIPT})
    SCRIPT_NAME=$(basename ${SCRIPT})
    SCRIPT_ROOT=$(dirname ${SCRIPT_DIR})
    SRC_DIR=$(dirname ${SCRIPT_ROOT})
    REPO_HOME=$(dirname ${SRC_DIR})
    DEPLOY_SRC=$(dirname ${REPO_HOME})
    GDG_PROFILE="${DEPLOY_SRC}/Dataset_Generator.profile"
fi

if [[ -f "${GDG_PROFILE}" ]]; then
    echo "Using configuration file at: ${GDG_PROFILE}"
    source "${GDG_PROFILE}"
else
    echo "$(basename ${GDG_PROFILE}) was not found. Unable to continue: ${GDG_PROFILE}"
    exit 1
fi

if [[ $# -eq 0 ]]
then
    echo ""
    echo "${DOCS}"
    echo ""
    exit 1
fi

while getopts "hi:a:s:b:o:" OPTION
do
    case $OPTION in
        h) echo ""; echo "${DOCS}" ; echo ""; exit 0 ;;
        i) SAMPLE_DIR="${OPTARG}" ;;
        a) ALIGNER="${OPTARG}" ;;
        s) FQ_TOOL="${OPTARG}" ;;
        b) BED_FILE="${OPTARG}" ;; 
        o) OUT_DIR="${OPTARG}" ;;
        ?) echo "${DOCS}" ; exit ;;
    esac
done

##################################################
#VERIFY REQUIRED PARMS
##################################################

if [[ -z ${SAMPLE_DIR} ]]; then
    echo "ERROR: Sample directory is a required input parm!";
    echo "${DOCS}";
    exit 1;
fi

if [[ ! -d ${SAMPLE_DIR} ]]; then
    echo "Sample directory does not exist: ${SAMPLE_DIR}";
    exit 1;
fi 
if [[ -z ${BED_FILE} ]]; then
    echo "ERROR: BED file is a required input parm!";
    echo "${DOCS}";
    exit 1;
fi

if [[ ! -f ${BED_FILE} ]]; then
    echo "ERROR: The path to the bed file is incorrect! Exiting...";
    exit 1;
fi

if [[ -z ${OUT_DIR} ]]; then
    echo "ERROR: Output folder is a required input parm!";
    echo "${DOCS}";
    exit 1;
fi

if [[ -d ${OUT_DIR} ]]; then
    echo "The output folder already exits! Exiting...";
    exit 1; #temporarily
fi

temppath1=`readlink -f ${SAMPLE_DIR}`
temppath2=`readlink -f ${OUT_DIR}`
if [[ $temppath1 == $temppath2 ]]; then
    echo "The sample and output directories must be different! Exiting...";
    exit 1;
fi

if [[ ! -z ${ALIGNER} ]]; then
    if [[ "${ALIGNER}" != "bwa" ]] && [[ "${ALIGNER}" != "bowtie" ]]; then
        echo "Aligner must be 'bwa' or 'bowtie'";
        exit
    fi
else
    ALIGNER="bwa"
fi

if [[ ! -z ${FQ_TOOL} ]]; then
    if [[ "${FQ_TOOL}" != "bedtools" ]] && [[ "${FQ_TOOL}" != "samtools" ]]; then
        echo "Fastq file restoration tool must be 'bedtools' or 'samtools'";
        exit
    fi
else
    FQ_TOOL="bedtools"
fi

gzfastqs=`find "$SAMPLE_DIR" -maxdepth 1 -iname "*.fastq.gz"`
if [[ -n ${gzfastqs} ]]; then
    echo "Decompressing fastq.gz files..."
    for f in ${gzfastqs}; do
        gunzip ${f}
    done
    sleep 1
fi

MODE=1
fastqs=`find "$SAMPLE_DIR" -maxdepth 1 -iname "*.fastq"`
if [[ ! -n ${fastqs} ]]; then
    echo "Fastq files do not exists! Checking bam files..."
    bams=`find "$SAMPLE_DIR" -maxdepth 1 -iname "*.bam"`
    if [[ ! -n ${bams} ]]; then
        echo "Neither fastq nor bam files exist! Exiting..."
        exit 1
    else
        echo "Only bam files are available"
        MODE=3
    fi
else
    echo "Fastq files are available. Including:" ${fastqs}
    test_aln=${SAMPLE_DIR}/aln1.bam
    if [[ -f ${test_aln} ]]; then
        echo "Alignments of fastq files have already been generated. Will skip this step!"
        MODE=2
    fi
fi

CMD_DIR=${OUT_DIR}/scripts
mkdir ${OUT_DIR}
mkdir ${CMD_DIR}

source ${GDG_PROFILE}
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}
echo "=====Configurations====="
echo "Aligner: ${ALIGNER}"
ALIGNER_PATH=${!ALIGNER}
echo "Aligner's path: ${ALIGNER_PATH}"
eval GENOME_INDEX=\${${ALIGNER}_index}
echo "Genome index: ${GENOME_INDEX}"
echo "Fastq restoration tool: ${FQ_TOOL}"
FQ_TOOL_PATH=${!FQ_TOOL}
echo "Fastq restoration tool's path: ${FQ_TOOL_PATH}"
echo "Selected chromosomal regions: ${BED_FILE}"
echo "Config file: ${CFG_FILE}"
echo "Number of threads: ${THREADS}"
echo "Running mode: ${MODE}"
cmd_generator=${SCRIPT_DIR}/generate_commands_tracks_1_2.py
cmd_generator2=${SCRIPT_DIR}/generate_commands_track_3.py
restore_script=${SCRIPT_DIR}/restore_fastq_new.py
if [[ ${MODE} -ne 3 ]]; then
    echo "Fastq files:"
    echo "${fastqs}"
    ${python} ${cmd_generator} ${ALIGNER} ${ALIGNER_PATH} ${GENOME_INDEX} ${SAMPLE_DIR} ${BED_FILE} ${OUT_DIR} ${MODE} ${samtools} ${bedtools} ${FQ_TOOL} ${python} ${LD_LIBRARY_PATH} ${restore_script} ${CFG_FILE} ${THREADS} ${sentieon} ${PYTHONHOME} ${fastqs}
else
    echo "Bam files:"
    echo "${bams}"
    ${python} ${cmd_generator2} ${SAMPLE_DIR} ${BED_FILE} ${OUT_DIR} ${samtools} ${bedtools} ${FQ_TOOL} ${bams}
fi
echo "Qsub scripts generated under ${CMD_DIR}"
DISPATCH="${QSUB} -q ${QUEUE} -l h_vmem=${HVMEM},h_stack=${HSTACK}"
#echo $DISPATCH
for f in `find "$CMD_DIR" -iname "*.sh" | uniq` ; do
    $DISPATCH $f
done
