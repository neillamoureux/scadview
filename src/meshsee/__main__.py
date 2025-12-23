if __name__ == "__main__":
    # Load modules only when needed to speed up initial import before showing splash
    import logging

    from meshsee.logging_main import configure_logging, parse_logging_level

    # setup_logging()
    LOG_QUEUE_SIZE = 1000
    DEFAULT_LOG_LEVEL = logging.WARNING

    logging_listener = configure_logging(DEFAULT_LOG_LEVEL)
    parse_logging_level()

    from meshsee.ui.splash import start_splash_process

    splash_conn = start_splash_process()
    from meshsee.app import main

    main(splash_conn)
