if __name__ == "__main__":
    # Load modules only when needed to speed up initial import before showing splash

    from meshsee.logging_main import (
        DEFAULT_LOG_LEVEL,
        configure_logging,
        parse_logging_level,
    )

    LOG_QUEUE_SIZE = 1000

    configure_logging(DEFAULT_LOG_LEVEL)
    parse_logging_level()

    from meshsee.ui.splash import start_splash_process

    splash_conn = start_splash_process()
    from meshsee.app import main

    main(splash_conn)
