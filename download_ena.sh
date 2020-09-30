#!/bin/bash
#BSUB -J ascp      # job name
#BSUB -n 1                   # number of tasks in job
#BSUB -e errors.%J     # error file name in which %J is replaced by the job ID
#BSUB -o output.%J     # output file name in which %J is replaced by the job ID

set -euxo pipefail 

#ROOT=$(dirname $(readlink -f "$0"))
#echo ${ROOT}
#exit

#for SRA in DRR014730 SRR12416444 SRR6796710
for SRA in $1
do
    bsub -o output.%J -e error.%J -N ${SRA} "python ena-fast-download.py ${SRA} "
done
