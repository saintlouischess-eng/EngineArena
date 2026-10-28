if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    import sys
    if '--broadcast' in sys.argv:
        sys.argv.remove('--broadcast')
        from arena.broadcast_server import main
    else:
        from arena.server import main
    main()
