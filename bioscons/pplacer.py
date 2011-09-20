"""
Builders
--------

"""

# we expect this to fail unless imported from within SConstruct
try:
    from SCons.Script import *
except ImportError:
    pass

from taxtastic.refpkg import Refpkg

from fileutils import rename
from infernal import cmalign_method, cmmerge_method

def pplacer(env, refpkg, alignment, outdir = None, options = None, nproc = 2):
    
    cmd = ['pplacer', '-j %i' % int(nproc)]

    if outdir:
        cmd.extend(['--out-dir', env.subst(outdir)])

    if options:
        cmd.append(options)

    cmd.extend(['-c', '$SOURCES'])
    
    return env.Command(
        target = rename(alignment, '.jplace'),
        source = Flatten([refpkg, alignment]),
        action = ' '.join(cmd)
        )
    
def align_and_place(env, refpkg, qseqs, outdir = None,
                    options = None, nproc = 1):

    """
    Align sequences in ``qseqs``, merge with the reference alignment,
    and run pplacer.

     * env - Environment instance.
     * refpkg - path to a reference package directory.
     * qseqs - unaligned query sequenecs in fasta format.
     * options - command line options to be provided to
       pplacer. Note that substitution of variables defined withon the
       current environment will occur.
     * outdir - optional output directory; saves files to same
       directory as qseqs if unspecified.
     * number of processors to use for ``cmalign`` and ``pplacer``.

    Returns (sto, scores, merged, placefile)

    Example::

        from bioscons.pplacer import align_and_place
        env.AddMethod(align_and_place, "align_and_place")    
        sto, scores, merged, placefile = env.AlignAndPlace(
            refpkg = 'my.refpkg', qseqs = 'myseqs.fasta',
            pplacer_options = '-p --inform-prior --map-identity'
        )
    """

    cmalign_options = '--hbanded --sub --dna -1'
    
    if not hasattr(env, 'cmalign_method'):
        env.AddMethod(cmalign_method, 'cmalign_method')

    if not hasattr(env, 'cmmerge_method'):
        env.AddMethod(cmmerge_method, 'cmmerge_method')

    if not hasattr(env, 'pplacer_method'):
        env.AddMethod(pplacer, 'pplacer_method')

    pkg = Refpkg(refpkg)        
    profile = pkg.file_abspath('profile')
    ref_sto = pkg.file_abspath('aln_sto')
    
    # align sequences
    sto, scores = env.cmalign_method(
        profile = profile,
        fasta = qseqs,
        nproc = nproc,
        options = cmalign_options,
        outdir = outdir
        )
    
    # merge with reference set
    merged = env.cmmerge_method(
        profile, ref_sto, sto,
        outname = rename(sto, '_merged.sto'),
        options = cmalign_options,
        outdir = outdir
        )

    # pplacer!    
    placefile = env.pplacer_method(
        refpkg = refpkg,
        alignment = merged,
        outdir = outdir,
        options = options,
        nproc = nproc
        )

    if outdir and not outdir == '.':
        Clean(placefile, Dir(outdir))
    
    return Flatten([sto, scores, merged, placefile])

