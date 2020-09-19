#!/usr/bin/env python3

__author__ = "Ben Woodcroft"
__copyright__ = "Copyright 2019"
__credits__ = ["Ben Woodcroft"]
__license__ = "GPL3+"
__maintainer__ = "Ben Woodcroft"
__email__ = "b.woodcroft near uq.edu.au"
__status__ = "Development"

import argparse
import logging
import subprocess
import sys
import warnings

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Quickly download FASTQ files from the European Nucleotide Archive (ENA) using aspera.\n\n'
        'Requires curl and ascp (i.e. aspera, see https://www.biostars.org/p/325010/#389254) to be in the $PATH.')
    parser.add_argument('run_identifier',help='Run number to download e.g. ERR1739691')
    parser.add_argument('--output-directory','--output_directory',help='Output files to this directory [default: \'.\']',default='.')
    parser.add_argument('--ssh-key','--ssh_key',help='\'linux\' or \'osx\' for default paths used in each OS respectively, \
    otherwise a path to the openssh key to used for aspera (i.e. the -i flag of ascp) [default: \'linux\']',
                        default='linux')
    parser.add_argument('--forward-only','--forward_only', action="store_true", help='Forward reads only')
    parser.add_argument('--reverse-only','--reverse_only', action="store_true", help='Reverse reads only')
    parser.add_argument('--ascp-args','--ascp_args',help='extra arguments to pass to ascp e.g. \'-k 2\' to resume with a \
        sparse file checksum [default: \'\']',default='')
    parser.add_argument('--debug', help='output debug information', action="store_true", default=False)
    parser.add_argument('--quiet', help='only output errors', action="store_true", default=False)
    args = parser.parse_args()

    if args.debug:
        loglevel = logging.DEBUG
    elif args.quiet:
        loglevel = logging.ERROR
    else:
        loglevel = logging.INFO
    logging.basicConfig(level=loglevel, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

    # Use the example set out at this very helpful post:
    # https://www.biostars.org/p/325010
    if bool(args.forward_only):
        assert bool(args.reverse_only) == False, "Cannot specify --forward-only and --reverse-only"
    if bool(args.reverse_only):
        assert bool(args.forward_only) == False, "Cannot specify --forward-only and --reverse-only"

    if args.ssh_key == 'linux':
        ssh_key_file = '$HOME/.aspera/connect/etc/asperaweb_id_dsa.openssh'
    elif args.ssh_key == 'osx':
        ssh_key_file = '$HOME/Applications/Aspera\ Connect.app/Contents/Resources/asperaweb_id_dsa.openssh'
    else:
        ssh_key_file = args.ssh_key
    logging.info("Using aspera ssh key file: {}".format(ssh_key_file))

    run_id = args.run_identifier
    output_directory = args.output_directory

    # Get the textual representation of the run. We specifically need the fastq_ftp bit
    logging.info("Querying ENA for FTP paths for {}..".format(run_id))
    query_url = "https://www.ebi.ac.uk/ena/portal/api/filereport?accession={}&result=read_run&fields=fastq_ftp".format(run_id)
    logging.debug("Querying '{}'".format(query_url))
    text = subprocess.check_output("curl --silent '{}'".format(query_url),shell=True)

    ftp_urls = []
    header=True
    logging.debug("Found text from ENA API: {}".format(text))
    for line in text.decode('utf8').split('\n'):
        logging.debug("Parsing line: {}".format(line))
        if header:
            header=False
        else:
            if line == '': continue
            fastq_ftp = line.split('\t')[1]
            for url in fastq_ftp.split(';'):
                if url.strip() != '': ftp_urls.append(url.strip())
    if len(ftp_urls) == 0:
        # One (current) example of this is DRR086621
        logging.error("No FTP download URLs found for run {}, cannot continue".format(run_id))
        sys.exit(1)
    else:
        logging.debug("Found {} FTP URLs for download: {}".format(len(ftp_urls), ", ".join(ftp_urls)))

    if len(ftp_urls) == 1:
        if bool(args.forward_only) or bool(args.reverse_only):
            warnings.warn("Specified --forward_only or --reverse_only but only a single read set found. Downloading the single read set.")
    else:
        if bool(args.forward_only):
            ftp_urls = list(filter(lambda filename: "_1.fastq" in filename , ftp_urls))
            if len(ftp_urls) != 1:
                logging.error("Unexpectedly found no read files that contain '_1.fastq' in their name")
                sys.exit(1)
            logging.info("Downloading forward only: {}".format(ftp_urls))
        elif bool(args.reverse_only):
            ftp_urls = list(filter(lambda filename: "_2.fastq" in filename , ftp_urls))
            if len(ftp_urls) != 1:
                logging.error("Unexpectedly found no read files that contain '_2.fastq' in their name")
                sys.exit(1)
            logging.info("Downloading reverse only: {}".format(ftp_urls))

    logging.info("Downloading {} FTP read set(s): {}".format(len(ftp_urls), ", ".join(ftp_urls)))

    aspera_commands = []
    for url in ftp_urls:
        quiet_args = ''
        if args.quiet:
            quiet_args = ' -Q'
        #cmd = "ascp{} -T -l 300m -P33001 {} -i {} era-fasp@fasp.sra.ebi.ac.uk:{} {}".format(
        cmd = "ascp{} -k2 -T -l 5m -P33001 {} -i {} era-fasp@fasp.sra.ebi.ac.uk:{} {}".format(
            quiet_args,
            args.ascp_args,
            ssh_key_file,
            url.replace('ftp.sra.ebi.ac.uk',''), output_directory)
        logging.info("Running command: {}".format(cmd))
        subprocess.check_call(cmd,shell=True)

logging.info("All done.")
