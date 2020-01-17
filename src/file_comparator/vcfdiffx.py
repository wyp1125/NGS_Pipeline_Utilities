#!/usr/bin/env python3
#
# vcfdiff.py
# Author: Gregory S Mendez
# The original program checks simple differences between VCF files.
#
# vcfdiffx.py
# Author: Yupeng Wang
# The upgraded version is able to report sophisticated differences between VCF files.
#
# Arguments:
# This script takes two arguments:
# 1) -r | --ref | The VCF file used as the reference.
# 2) -n | --new | The new VCF file being assessed for differences from the reference.
# 3) -o | --out | Running/Output directory.
# 4) -c | --config | A file in DEPENDENCY=/full/file/path format for all dependencies
#
# Dependencies:
#   TABIX
#   BGZIP

import argparse
import collections
import os
import sys
import re
import logging
import shutil
from subprocess import check_call
from subprocess import Popen

__version__ = '2.0'

###########################################################################
# Configure Logging #
###########################################################################
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Never change
logging_format = '%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s'
screen_handler = logging.StreamHandler()
# Change this to reduce screen level verbosity
screen_handler.setLevel(logging.INFO)
screen_handler.setFormatter(logging.Formatter(logging_format))
logger.addHandler(screen_handler)

###########################################################################
# Argument Parser #
###########################################################################
def get_cli_opts(my_conf):
    mydesc = """
This script compares two VCF files disregarding the order of genetic variants.
"""
    parser = argparse.ArgumentParser(description=mydesc, formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-r', '--ref', type=str, required=True, help="The reference VCF file.")
    parser.add_argument('-n', '--new', type=str, required=True, help="New VCF for comparison.")
    parser.add_argument('-o', '--out', type=str, required=True, help="Output directory.")
    parser.add_argument('-c', '--config', type=str, required=True, help="File with file paths of all depenedencies.")
    parser.add_argument('-d', '--debug', help="add debugging messages to output", action="store_true")
    my_args = parser.parse_args()
    # Check if paths are good
    check_args(my_args)
    
###########################################################################
    # upgrade: move vcf files to output dir
    vcf1_file=os.path.basename(my_args.ref)
    vcf2_file=os.path.basename(my_args.new)
    vcf1_dir=os.path.join(os.path.abspath(my_args.out),"vcf1")
    vcf2_dir=os.path.join(os.path.abspath(my_args.out),"vcf2")
    create_folder_or_fail(vcf1_dir)
    create_folder_or_fail(vcf2_dir)
    shutil.copy2(os.path.abspath(my_args.ref),vcf1_dir)
    shutil.copy2(os.path.abspath(my_args.new),vcf2_dir)
    vcf1_path=os.path.join(vcf1_dir,vcf1_file)
    vcf2_path=os.path.join(vcf2_dir,vcf2_file)
    
    # upgrade: check vcf.gz files and return paths of uncompressed vcf files
    my_conf["logfile"]=os.path.join(os.path.abspath(my_args.out),"main.log")
    my_conf["old_file"] = check_vcfgz(vcf1_path)
    my_conf["new_file"] = check_vcfgz(vcf2_path)
###########################################################################

    my_conf["outdir"] = os.path.abspath(my_args.out)
    my_conf["config"] = os.path.abspath(my_args.config)
    # Non-required
    my_conf["debug"] = my_args.debug
    return

# Read the configuration file specified on the cli options
def get_conf_opts(my_conf):
    valid_opts = {"TABIX", "BGZIP"}

    with open(my_conf["config"], 'r') as config_file:
        for line in config_file:
            line = line.rstrip()
            if line and not line.startswith("#"):
                myarr = line.split("=")
                key = myarr[0]
                if len(myarr) > 1:
                    value = myarr[1]
                else:
                    value = ''
                if key in valid_opts:
                    my_conf[key] = re.sub(r'^"|"$', '', value)
                    logger.info("Parsed key={0},value={1}".format(key, value))

    check_dependencies(my_conf)

    missing = list()

    for opt in valid_opts:
        if opt not in my_conf.keys():
            missing.append(opt)

    if len(missing) > 0:
        msg = "Missing the following required configuration options {!s}".format(missing)
        e = RuntimeError(msg)
        raise e

    return


class VcfDiffConfig:
    class __VcfDiffConfig:
        """Object for storing VcfDiff configuration settings

            Validation for anything other than correct type should be handled elsewhere.

        """

        def __init__(self, configuration):
            # a dictionary containing key, value pairs for the following keys:
            # "old_file", "new_file", "outdir", "debug", "verbose"

            self.__old_file = configuration["old_file"]
            self.__new_file = configuration["new_file"]
            self.__outdir = configuration["outdir"]

            self.__BGZIP = os.path.abspath(str(configuration["BGZIP"]))
            self.__TABIX = os.path.abspath(str(configuration["TABIX"]))

            if configuration["debug"]:
                self.__debug = True
            else:
                self.__debug = False

    @property
    def old_file(self):
        return self._instance.__old_file

    @property
    def new_file(self):
        return self._instance.__new_file

    @property
    def outdir(self):
        return self._instance.__outdir

    @property
    def debug(self):
        return self._instance.__debug

    @property
    def bgzip(self):
        return self._instance.__BGZIP

    @property
    def tabix(self):
        return self._instance.__TABIX

    _instance = None

    def __init__(self, arg):
        if not VcfDiffConfig._instance:
            VcfDiffConfig._instance = VcfDiffConfig.__VcfDiffConfig(arg)
        else:
            raise RuntimeError('Attempt to re-instantiate configuration.')


###########################################################################
# Functions ###
###########################################################################

def get_filename(my_path):
    msplit = str(my_path).split("/")
    return msplit[len(msplit) - 1]

def file_write_or_fail(path):
    try:
        with open(path, 'w'):
            pass
    except IOError as e:
        print("{!s}: {!s}".format(e.strerror, e.filename))
        logger.exception(e.strerror)
        exit(1)

def file_read_or_fail(path):
    try:
        with open(path, 'r'):
            pass
    except IOError as e:
        print("{!s}: {!s}".format(e.strerror, e.filename))
        logger.exception(e.strerror)
        exit(1)
    return

def create_folder_or_fail(path):
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        print("{!s}: {!s}".format("Can't create or access folder:", path))
        logger.exception(e.strerror)
        exit(1)
    return

def check_args(my_args):
    # Try to open each input file for reading
    file_read_or_fail(my_args.ref)
    file_read_or_fail(my_args.new)
    file_read_or_fail(my_args.config)
    create_folder_or_fail(my_args.out)
    return

def check_dependencies(my_conf):
    depenedencies = {"BGZIP", "TABIX"}
    for my_dep in depenedencies:
        file_read_or_fail(my_conf[my_dep])
    return

################################################
#upgrade: check vcf.gz file type and gunzip if so
def check_vcfgz(path):
    newpath=path
    _, ext = os.path.splitext(newpath)
    if ext==".gz":
       check_call(['gunzip', path])
       newpath=path[:-3]
    if ext==".zip":
       check_call(['unzip', path])
       newpath=path[:-4]
    check_call(["sleep","1"])
    return newpath

#upgrade: prefix "chr" in chromsome IDs should not matter in comparisons
def smart_chr(name):
    new_name=name
    if re.match("chr[\dXYMG]+",new_name)!=None:
        new_name=name[3:]
    return new_name
################################################

def redirect_to_file(cmd, path):
    original = sys.stdout
    # sys.stdout = open(path, 'w')
    print(cmd)
    sys.stdout = original

# Call bgzip to compress a file
def bgzip(filename, path):
    proc = Popen(vcfd.bgzip+" -c "+filename+" > "+path, shell=True)
    proc.wait()

# Call tabix to index a vcf file
def tabix_index(filename):
    check_call([vcfd.tabix, '-p', 'vcf', filename])

def set_file_logging(my_conf):
    formatter = logging.Formatter('%(asctime)s :[%(levelname)s] - %(filename)s - %(message)s')
    my_handler = logging.FileHandler(my_conf["logfile"], mode="w")
    if my_conf["debug"]:
        my_handler.setLevel(logging.DEBUG)
    else:
        my_handler.setLevel(logging.INFO)
    my_handler.setFormatter(formatter)
    logger.addHandler(my_handler)
    return

# sort, bgzip and index file
#Upgrade: direct to new paths
def vcf_prep(filepath):
    gz_out = ("%s.gz" % (filepath))
    bgzip(filepath, gz_out)
    filename = gz_out
    tabix_index(filename)
    return filename

# Ignore comment/header/empty lines from input VCF file so that only the
# actual calls are compared.
###############################################################
# Upgrade: left trim "chr" at the beginning of each line
def strip_header(input):
    with open(input, "r") as myfile:
        my_list = []
        for line in myfile:
            li = line.strip()
            # Ignores the comment lines
            if not li.startswith("#"):
                # Ignore empty lines
                if len(li) > 0:
                    my_list.append(li)
#                    my_list.append(li.lstrip('chr')) #add left trim
    return my_list
###############################################################

# Retrieve comment/header from input VCF file
def just_header(input):
    with open(input, "r") as myheader:
        my_list = []
        for line in myheader:
            li = line.strip()
            # Get the comment/header lines
            if li.startswith("#"):
                # Ignore empty lines
                if len(li) > 0:
                    my_list.append(li)
    return my_list

##############################################################
# Upgrade: retrieve different sections of VCF files
def get_partitions(input):
    vt_list = []
    vt_gt_list = []
    vid_list = []
    ann_list = []
    mtc_fld_list = []
    mtc_cmb_list = []
    for element in input:
        split_element = element.split('\t')
        chrID=smart_chr(split_element[0])
        tmp_list1=[]
        tmp_list1.append(chrID)
        tmp_list1=tmp_list1+split_element[1:2]+split_element[3:5]
        tmp_list2=tmp_list1
        tmp_list3=split_element[8].split(":")
        for word in tmp_list3[1:]:
            mtc_fld_list.append(word)
        for gt in split_element[9:]:
            tmp_list4=gt.split(':')
            tmp_list2.append(tmp_list4[0])
            for i in range(1,len(tmp_list4)):
                mtc_cmb_list.append(tmp_list3[i]+':'+tmp_list4[i])
        vt_list.append("\t".join(tmp_list1))
        vt_gt_list.append("\t".join(tmp_list2))
        if split_element[2]!='.':
            vid_list.append(str(split_element[2]))
        if split_element[7]!='.':
            ann_list.append(split_element[7])
    return vt_list, vt_gt_list, vid_list, ann_list, mtc_fld_list, mtc_cmb_list

#Upgrade: further partition inform fields and values by the first '='
def get_fields_values(input):
    field_list = []
    value_list = []
    fld2val_list = []
    for element in input:
        units = element.split(';')
        for eachUnit in units:
            if re.search("=",eachUnit):
                fld2val_list.append(eachUnit)
                word=eachUnit.split('=', maxsplit=1)
                field_list.append(word[0])
                if word[1]!='.':
                    value_list.append(str(word[1]))
    return field_list, value_list, fld2val_list
#############################################################
# Upgrade: write the contents of dicts to files in descending order
def output_dict(x,fname):
    out_path=os.path.join(vcfd.outdir,fname)
    if len(x)>0:
        with open(out_path,'w') as of:
            for key in sorted(x.items(),key=lambda a:(a[1],a[0]),reverse=True):
                of.write(key[0]+'\t'+str(key[1])+'\n')
def output_dict1(x,fname):
    out_path=os.path.join(vcfd.outdir,fname)
    if len(x)>0:
        with open(out_path,'w') as of:
            for key in sorted(x.items(),key=lambda a:(abs(a[1][0]-a[1][1]),a[0]),reverse=True):
                of.write(key[0]+'\t'+str(key[1][0])+'\t'+str(key[1][1])+'\n')

# Upgrade: display comparisons of two dicts
def report_dict_comparisons(x_ad,x_rm,x_md,x_sm, mode):
    temp=compute_num(x_ad)
    logger.info("\t\tAdded "+mode+": "+str(temp))
    temp=compute_num(x_rm)
    logger.info("\t\tRemoved "+mode+": "+str(temp))
    temp=compute_num1(x_md)
    logger.info("\t\tModified "+mode+": "+str(temp))
    temp=compute_num(x_sm)
    logger.info("\t\tSame "+mode+": "+str(temp))

# Comparison using counters so that duplicates are noticed.
def simple_compare(x, y): 
    return collections.Counter(x) == collections.Counter(y)
##############################################################
#Upgrade: add complex comparison
def complex_compare(x, y):
    d1=collections.Counter(x)
    d2=collections.Counter(y)
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    added = {o : d2[o] for o in (d2_keys - d1_keys)}
    removed = {o : d1[o] for o in (d1_keys - d2_keys)}
    modified = {o : (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
    same = {o : d1[o] for o in intersect_keys if d1[o] == d2[o]}
    return added, removed, modified, same

def compute_num(x):
    n=0
    for key in x:
        n=n+x[key]
    return n

def compute_num1(x):
    n=0
    for key in x:
        n=n+x[key][0]
    return n
#############################################################

if __name__ == '__main__':
    ###########################################################################
    # Configuration. #
    ###########################################################################
    # dictionary containing run options
    conf_dict = dict()
    # parse and check the command line options
    get_cli_opts(conf_dict)
    # set up logging
    set_file_logging(conf_dict)
    # parse and check the config file options
    get_conf_opts(conf_dict)
    # create the configuration object and validate the options
    vcfd = VcfDiffConfig(conf_dict)

    ###########################################################################
    # Upgrade: Compare the VCF files. Previous procedure is mostly modified
    ###########################################################################
    logger.info("Reference VCF: "+vcfd.old_file)
    logger.info("New VCF: "+vcfd.new_file)
    vcf_prep(vcfd.old_file)
    vcf_prep(vcfd.new_file)
    logger.info("Indexing the VCF files...")
    # Separate the header from the variants so we can compare separately
    header_old = just_header(vcfd.old_file)
    header_new = just_header(vcfd.new_file)
    pure_vcf_old = strip_header(vcfd.old_file)
    pure_vcf_new = strip_header(vcfd.new_file)

    # Check if the headers are identical, though it won't affect subsequent comparisons
    logger.info("Performing simple comparisons...")
    logger.info("Comparing headers...")
    if simple_compare(header_old, header_new):
        logger.info("\t\tHeaders are identical.")
    else:
        logger.info("\t\tHeaders are different.")
   
    # Check if the variation lines are completely identical. If so, exit
    logger.info("Comparing main VCFs...")
    if simple_compare(pure_vcf_old, pure_vcf_new):
        logger.info("\t\tMain VCFs are identical.")
        logger.info("No further analysis is needed.")
        exit(0)

    logger.info("\t\tMain VCFs are different!")
    logger.info("Performing sophisticated comparisons...")
    # Upgrade: retrieve different sections of vcf files
    vt_old, vt_gt_old, vid_old, ann_old, mtc_fld_old, mtc_cmb_old = get_partitions(pure_vcf_old)
    vt_new, vt_gt_new, vid_new, ann_new, mtc_fld_new, mtc_cmb_new = get_partitions(pure_vcf_new)
    # Upgrade: different levels of comparisons
    logger.info("Comparing variants only...")
    res_ad,res_rm,res_md,res_sm=complex_compare(vt_old,vt_new)
    report_dict_comparisons(res_ad,res_rm,res_md,res_sm,"variants")
    output_dict(res_ad,"added_variants")
    output_dict(res_rm,"removed_variants")
    output_dict1(res_md,"modified_variants")

    logger.info("Comparing variants + genotypes...")
    res_ad,res_rm,res_md,res_sm=complex_compare(vt_gt_old,vt_gt_new)
    report_dict_comparisons(res_ad,res_rm,res_md,res_sm,"variants/genotypes")
    output_dict(res_ad,"added_variants_genotypes")
    output_dict(res_rm,"removed_variants_genotypes")
    output_dict1(res_md,"modified_variants_genotypes")
    
    logger.info("Comparing variant IDs")
    res_ad,res_rm,res_md,res_sm=complex_compare(vid_old,vid_new)
    report_dict_comparisons(res_ad,res_rm,res_md,res_sm,"variant IDs")
    output_dict(res_ad,"added_variant_IDs")
    output_dict(res_rm,"removed_variant_IDs")
    output_dict1(res_md,"modified_variant_IDs")

    ann_field_old,ann_value_old,fld2val_old=get_fields_values(ann_old)
    ann_field_new,ann_value_new,fld2val_new=get_fields_values(ann_new)
    logger.info("Comparing annotation fields")
    res_ad,res_rm,res_md,res_sm=complex_compare(ann_field_old,ann_field_new)
    report_dict_comparisons(res_ad,res_rm,res_md,res_sm,"annotation fields")
    output_dict(res_ad,"added_annotation_fields")
    output_dict(res_rm,"removed_annotation_fields")
    output_dict1(res_md,"modified_annotation_fields")

    logger.info("Comparing annotation values")
    res_ad,res_rm,res_md,res_sm=complex_compare(ann_value_old,ann_value_new)
    report_dict_comparisons(res_ad,res_rm,res_md,res_sm,"annotation values")
    output_dict(res_ad,"added_annotation_values")
    output_dict(res_rm,"removed_annotation_values")
    output_dict1(res_md,"modified_annotation_values")

    logger.info("Comparing metrics fields")
    res_ad,res_rm,res_md,res_sm=complex_compare(mtc_fld_old,mtc_fld_new)
    report_dict_comparisons(res_ad,res_rm,res_md,res_sm,"metrics fields")
    output_dict(res_ad,"added_metrics_fields")
    output_dict(res_rm,"removed_metrics_fields")
    output_dict1(res_md,"modified_metrics_fields")

    logger.info("Comparing metrics values")
    res_ad,res_rm,res_md,res_sm=complex_compare(mtc_cmb_old,mtc_cmb_new)
    report_dict_comparisons(res_ad,res_rm,res_md,res_sm,"metrics values")
    output_dict(res_ad,"added_metrics_values")
    output_dict(res_rm,"removed_metrics_values")
    output_dict1(res_md,"modified_metrics_values")
