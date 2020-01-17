#!/usr/bin/env python3
#
# check_deployments.py
#
# Author: Yupeng Wang
# 
# This program extracts deployment information for a pipeline to quickly identify deployment problems.
# This program assesses all deployments of a pipeline under prod, sandbox, qa and dev.
# 
# Arguments:
# This python3 program takes one required and one optional arguments:
# -p | --pname | the exact pipeline name
# -d | --debug | in debugging mode (optional)
######################
import argparse
import os,sys
import re
import subprocess

git="/usr/local/biotools/git/2.8.0/bin/git"

mydesc = """
This program extracts deployment information for a pipeline to quickly identify deployment problems.
This program assesses all deployments of a pipeline under prod, sandbox, qa and dev.
"""

parser = argparse.ArgumentParser(description=mydesc, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('-p', '--pname', type=str, required=True, help="the exact pipeline name")
parser.add_argument('-d', '--debug', action='store_true', help="in debugging mode (optional)")
my_args = parser.parse_args()
debugging=my_args.debug
pname=my_args.pname

def runcmd(command):
  process=subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  output=process.communicate()[0]
  exitCode=process.returncode
  if exitCode==0:
    return output
  else:
    return "NA"

def format_out(space,raw):
  line=raw.splitlines()
  rline=[]
  for eachLine in line:
    if len(eachLine.strip())>0:
      rline.append(eachLine)
  new_out=space+rline[0]
  n=len(rline)
  if n>1:
    for i in range(1,n):
        new_out=new_out+"\n"+space+rline[i]
  return new_out

super_dir_names=["prod","sandbox","qa","dev"]
check_dir_names=["prod","sandbox"]
check_dir_names_2=["sandbox","qa"]

for eachDirName in super_dir_names:
  pipeline_path=os.path.join("/dlmp",eachDirName,"scripts/deployments",pname)
  print("\nChecking in {}".format(eachDirName))
  if debugging:
    print("Pipeline directory: "+pipeline_path)
  if not os.path.isdir(pipeline_path):
    print("Pipeline name is incorrect or pipeline folder is missing")
    continue
  else:
    if debugging:
      print("Checking the pipeline directory...")
    items=os.listdir(pipeline_path)
    deploy_file_check=0
    property_file_check=0
    deployments=[]
    for eachItem in items:
      good_file_check=0
      if re.search("deploy.sh",eachItem):
        deploy_file_check=1
        good_file_check=1
      if re.search("properties",eachItem):
        property_file_check=1
        good_file_check=1
      if re.search("[\d]+.[\d]+.[\d]+",eachItem):
        if re.search("^[vV]?\d.\d\d.\d\d$",eachItem):
          deployments.append(eachItem)
          good_file_check=1
        else:
          print("    !!!Alert: "+eachItem+" looks like a deployment, but its naming is incorrect!")
          good_file_check=-1
      if good_file_check==0:
        print("    !!!Alert: "+eachItem+" is a redundant file")
    if deploy_file_check==0:
        print("    !!!Alert: deploy.sh is missing")
    if property_file_check==0:
        print("    !!!Alert: .property file is missing")
    if len(deployments)==0:
      print("    !!!Alert: No version deployments were found!")
    else:
      deployments.sort()
      if eachDirName=="prod":
        prod_deployments=set(deployments)
      if eachDirName in check_dir_names_2:
        curr_deployments=set(deployments)
        miss_deployments=prod_deployments.difference(curr_deployments)
        if len(miss_deployments)>0:
          print("    The following deployments are missing: "+", ".join(miss_deployments))
      print("    "+str(len(deployments))+ " deployment(s) were found, including: "+', '.join(deployments))
    for ffname in deployments:
      print("    Assessing deployment: "+ffname)
      src_dir=os.path.join(pipeline_path,ffname,"src")
      if not os.path.isdir(src_dir):
        print("    !!!Alert: There is NO src folder under this deployment!")
        continue
      src_items=os.listdir(src_dir)
      for eachItem in src_items:
        if re.search("LPEA_CAD",eachItem):
          print("        Assessing repository: "+eachItem)
          src_path=os.path.join(src_dir,eachItem)
          if debugging:
            print("Checking git status...")
          git_check=1
          git_error_msg=""
          os.chdir(src_path)
          cmd=git+" status"
          info=runcmd(cmd)
          if info == "NA":
            git_check=0
            git_error_msg="!!!Alert: Cannot obtain git status"
            if debugging:
              print("Cannot obtain git status")
          else:
            git_status_out=info.decode('utf-8')
            if debugging:
              print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
              print("Git status information:\n"+format_out("  ",git_status_out))
              print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
            if re.search("staged",git_status_out,re.IGNORECASE) or re.search("Untracked",git_status_out,re.IGNORECASE):
              git_check=0
              git_error_msg=git_error_msg+"\n!!!Alert: Source files were modified after deployment!"
              if debugging:
                print("            !!!Alert:Source files were modified after deployment!")
            keyword=''
            p1=re.compile("HEAD detached [atfrom]+ (.*)")
            hit1=p1.search(git_status_out)
            if hit1:
              keyword=hit1.group(1)
            else:
              p2=re.compile("On branch (.*)")
              hit2=p2.search(git_status_out) 
              if hit2:
                keyword=hit2.group(1)
            if debugging:
              print("Keyword: {}".format(keyword))
            if eachDirName in check_dir_names:
              if re.search(pname,eachItem,re.IGNORECASE):
                if not re.search(ffname,keyword):
                  git_check=0
                  git_error_msg=git_error_msg+"\n!!!Alert: tag name "+keyword+" does not match version name "+ffname+" under Prod/Sandbox!"
                  if debugging:
                    print("            !!!Alert: Tag name {} does not match version name {} under Prod/Sandbox!".format(keyword,ffname))
            cmd=git+" show-ref | grep "+keyword
            info=runcmd(cmd)
            if info == "NA":
              git_check=0
              git_error_msg=git_error_msg+"\n!!!Alert: Could not get git ref information"
              if debugging:
                print("            !!!Alert: Could not get git ref information")
            else:
              git_ref_out=info.decode('utf-8')
              if debugging:
                print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                print("Git ref information:\n"+format_out("  ",git_ref_out))
                print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
              commit_code=git_ref_out.split('\n')[0].split(' ')[0]
              cmd=git+" branch -a --contains "+commit_code
              info=runcmd(cmd)
              if info == "NA":
                git_check=0
                git_error_msg=git_error_msg+"\n!!!Alert: Could not obtain branch information"
                if debugging:
                  print("            !!!Alert: Could not obtain branch information")
              else:
                git_branch_out=info.decode('utf-8')
                if debugging:
                  print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
                  print("Git branch information:\n"+format_out("  ",git_branch_out))
                  print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
                if re.search(pname,eachItem,re.IGNORECASE):
                  if eachDirName in check_dir_names:
                    if re.search("master",git_branch_out,re.IGNORECASE) is None:
                      git_check=0
                      git_error_msg=git_error_msg+"\n!!!Alert: Branch is NOT on master under Prod/Sandbox!"
                      if debugging:
                        print("            !!!Alert: Branch is NOT on master under Prod/Sandbox!")
                  if eachDirName == "qa":
                    if re.search("release",git_branch_out,re.IGNORECASE) is None:
                      git_check=0
                      git_error_msg=git_error_msg+"\n!!!Alert: Branch is NOT on release under QA"
                      if debugging:
                        print("            !!!Alert: Branch is NOT on release under QA")
          if git_check==0:
            print("\n"+format_out("            ",git_error_msg)+"\n")
            if debugging:
              print("!!!Alert: Git check FAILED for {}, {}, {}.\n".format(eachItem,ffname,eachDirName))
          else:
            if debugging:
              print("Git check PASSED for {}, {}, {}.\n".format(eachItem,ffname,eachDirName))                       
