"""Known resource option aliases; never infer resources from substring matches."""
THREAD_NAMES=('Threads','Number of Threads','MaxThreads','Max CPUs')


def find_name(options,name):
    names=THREAD_NAMES if name.casefold()=='threads' else (name,)
    lookup={k.casefold():k for k in options}
    return next((lookup[n.casefold()] for n in names if n.casefold() in lookup),None)
