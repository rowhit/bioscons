import itertools
import subprocess
import ConfigParser
import tempfile
import shutil
import random
from os.path import join,split,splitext
import os.path

try:
    from SCons.Script import *
except ImportError:
    # we expect this to fail unless imported from within SConstruct
    pass

try:
    import Seq
except ImportError:
    Seq = None
    
# copyfile
def copyfile_emitter(target, source, env):
    """
    target - name of file or directory
    source - filename
    """

    sname = str(source[0])
    tname = str(target[0])
    if os.path.isdir(tname):
        target = join(tname, split(sname)[1])

    return target, source

copyfile = Builder(
    emitter=copyfile_emitter,
    action='cp $SOURCE $TARGET'
    )

def sample_wr(population, k):
    "Chooses k random elements (with replacement) from a population"
    n = len(population)
    _random, _int = random.random, int  # speed hack
    #return [_int(_random() * n) for i in itertools.repeat(None, k)]
    return [population[_int(_random() * n)] for i in itertools.repeat(None, k)]

# tofasta
def sto2fasta_action(target, source, env):
    """
    target = [aligned seqs in fasta format]
    source = [stockhom format alignment]
    """

    seqs = Seq.io_stockholm.read(open(str(source[0])).read(),
                                 case='upper',
                                 keep_struct=False,
                                 keep_ref=False)

    open(str(target[0]),'w').write(Seq.io_fasta.write(list(seqs)))

sto2fasta = Builder(action=sto2fasta_action)

def mergedToFasta_action(target, source, env):
    """
    Generate separate fasta files from a merged Stockholm alignment

    Can limit number of sequences from the command line using scons
    qcount=number

    
    target = [refalign.fasta, qalign.fasta]
    source = [refalign.sto, merged.sto]
    """

    refalign, merged = source
    refout, qout = target

    # count sequences in refalign.sto
    keep = lambda x: x.strip() and not (x.startswith('#') or x.startswith('/'))

    with open(str(refalign)) as infile:
        refnames = set(line.split()[0] for line in infile if keep(line))
        ref_seq_count = len(refnames)

    try:
        qcount = int(env['qcount'])
    except (ValueError, KeyError):
        qcount = None
        qstop = None
    else:
        qstop = ref_seq_count + qcount

    with open(str(merged)) as infile:
        seqs = Seq.io_stockholm.read(infile.read(),
                                     case='upper',
                                     keep_struct=False,
                                     keep_ref=False)

    refseqs = itertools.islice(seqs, ref_seq_count)
    with open(str(refout),'w') as outfile:
        outfile.write(Seq.io_fasta.write(list(refseqs)))

    qseqs = itertools.islice(seqs, ref_seq_count, qstop)
    with open(str(qout),'w') as outfile:
        outfile.write(Seq.io_fasta.write(list(qseqs)))

mergedToFasta = Builder(action=mergedToFasta_action)


def fa_to_seqmat_action(target, source, env):
    """
    Read a fasta format alignment and save a binary sequence matrix (package ape)
    """

    infile, outfile = source[0],target[0]

    rcmd = """library(ape)
    seqmat <- read.dna("%(infile)s", format="fasta", as.matrix=TRUE)
    save(seqmat, file="%(outfile)s")
    stopifnot(file.exists("%(outfile)s"))
    q()""" % locals()

    p = subprocess.Popen(["R", "--vanilla"], stdin=subprocess.PIPE, stdout=sys.stdout)
    p.communicate(rcmd)

fa_to_seqmat = Builder(action=fa_to_seqmat_action)

# stockholm format to phylip (replace names in phylip file to make
# raxml happy)
def sto2phy_emitter(target, source, env):
    # emits target = phylip alignment, namesfile
    sourcename = str(source[0]).replace('.sto','')
    target = [sourcename+'.phy', sourcename+'_names.txt']
    return target, source

sto2phy = Builder(
    action='sto2other.py -f $SOURCE -F phylip --numbers=${TARGETS[1]} > ${TARGETS[0]}',
    emitter=sto2phy_emitter)

# replace original names
rename = Builder(
    action='namerepl.py -f ${SOURCES[0]} -m ${SOURCES[1]} -o $TARGET')

