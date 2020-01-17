#!/usr/bin/env python3
#
# check_obsoleteness.py
#
# Author: Yupeng Wang
# 
# This program assesses all pipeline deployments under prod, sandbox, qa and dev, and identifies those which are not the most recent version and not dependencies of other pipelines' deployments.
# 
# Arguments:
# This python3 program takes one optional argument:
# -d | --debug | in debugging mode (optional)

import argparse
import os,sys
import re
import subprocess

mydesc = """
This program assesses all pipeline deployments under prod, sandbox, qa and dev, and identifies those which are not the most recent version and not dependencies of other pipelines' deployments.
"""
parser = argparse.ArgumentParser(description=mydesc, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('-d', '--debug', action='store_true', help="in debugging mode (optional)")
my_args = parser.parse_args()
debugging=my_args.debug

def runcmd(command):
  process=subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  output=process.communicate()[0]
  exitCode=process.returncode
  if exitCode==0:
    return output
  else:
    return "NA"

def trim_out(raw):
  lines=raw.splitlines()
  nlines=""
  if len(lines)>0:
    for eachLine in lines:
      if len(eachLine.strip())>0:
        if nlines=="":
          nlines=eachLine.strip()
        else:
          nlines=nlines+"\n"+eachLine.strip()
  return nlines

super_dir_names=["prod","sandbox","qa","dev"]
for eachDirName in super_dir_names:
  deploy_dir=os.path.join("/dlmp",eachDirName,"scripts/deployments")
  pips=os.listdir(deploy_dir)
  all_pipelines=[]
  all_deployments=[]
  all_paths=[]
  all_isRecent=[]
  all_times=[]
  all_dpts=[]
  all_profile_loc=[]
  all_profile_pip=[]
  all_profile_dep=[]
  for eachPip in pips:
    pip_dir=os.path.join(deploy_dir,eachPip)
    if os.path.isdir(pip_dir):
      items=os.listdir(pip_dir)
      deployments=[]
      versions=[]
      for eachItem in items:
        if re.search("^[vV]?\d.\d\d.\d\d$",eachItem):
          deployments.append(eachItem)
          ptn=re.compile("(\d.\d\d.\d\d)")
          hit=ptn.search(eachItem)
          if hit:
            versions.append(hit.group(1))
      n_deploy=len(deployments)
      if n_deploy>0:
        if n_deploy>1:
          version_idx=sorted(range(len(versions)),key=versions.__getitem__)
          i=0
          for pos in version_idx:
            all_pipelines.append(eachPip)
            all_deployments.append(deployments[pos])
            all_paths.append(os.path.join(pip_dir,deployments[pos]))
            cmd="find "+os.path.join(pip_dir,deployments[pos])+" -name *.profile"
            info=runcmd(cmd)
            if info != "NA":
              profile_file_output=trim_out(info.decode('utf-8'))
              if profile_file_output!="":
                profile_files=profile_file_output.split("\n")
                for eachProfile in profile_files:
                  all_profile_loc.append(eachProfile)
                  all_profile_pip.append(eachPip)
                  all_profile_dep.append(deployments[pos])
            all_times.append(0)
            if i==n_deploy-1:
              all_isRecent.append(True)
            else:
              all_isRecent.append(False)
            all_dpts.append("")
            i=i+1
        else:
            all_pipelines.append(eachPip)
            all_deployments.append(deployments[0])
            all_paths.append(os.path.join(pip_dir,deployments[0]))
            cmd="find "+os.path.join(pip_dir,deployments[0])+" -name *.profile"
            info=runcmd(cmd)
            if info != "NA":
              profile_file_output=trim_out(info.decode('utf-8'))
              if profile_file_output!="":
                profile_files=profile_file_output.split("\n")
                for eachProfile in profile_files:
                  all_profile_loc.append(eachProfile)
                  all_profile_pip.append(eachPip)
                  all_profile_dep.append(deployments[0])
            all_times.append(0)
            all_dpts.append("")
            all_isRecent.append(True)
  for i in range(0,len(all_deployments)):
    dpt_pips=""
    for j in range(0,len(all_profile_loc)):
      cmd="grep "+all_paths[i]+" "+all_profile_loc[j]
      info=runcmd(cmd)
      if info != "NA":
        hit_output=trim_out(info.decode('utf-8'))  
        if hit_output!="" and all_pipelines[i]!=all_profile_pip[j]:
          if dpt_pips=="":
            dpt_pips=all_profile_pip[j]+"-"+all_profile_dep[j]
          else:
            dpt_pips=dpt_pips+","+all_profile_pip[j]+"-"+all_profile_dep[j]
          all_times[i]=all_times[i]+1
          all_dpts[i]=dpt_pips
    status="Nonobsolete"
    if all_isRecent[i]==True:
      status="recent"
    else:
      status="OBSOLETE"
      if all_times[i]>0:
        status="nonobsolete"
    if debugging:
      print(eachDirName+"\t"+all_pipelines[i]+"\t"+all_deployments[i]+"\t"+status)
      if all_times[i]>0:
        print("\t\tcalled by: "+all_dpts[i])
    else:
      if status=="OBSOLETE":
        print(eachDirName+"\t"+all_pipelines[i]+"\t"+all_deployments[i]+"\t"+status)
