if __name__ == "__main__":
    # Load modules only when needed to speed up initial import before showing splash
    import logging

    from meshsee.logging_main import configure_logging, get_logging_level_from_args

    # setup_logging()
    LOG_QUEUE_SIZE = 1000
    DEFAULT_LOG_LEVEL = logging.WARNING

    log_level = get_logging_level_from_args()
    logging_listener = configure_logging(DEFAULT_LOG_LEVEL, main_process_level=log_level)
    logging.getLogger().setLevel(level=log_level)

    from meshsee.ui.splash import start_splash_process

    splash_conn = start_splash_process(log_level)
    from meshsee.app import main

    main(splash_conn)
