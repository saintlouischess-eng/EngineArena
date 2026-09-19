if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    from arena.server import main
    main()
