if __name__ == "__main__":
    # Load modules only when needed to speed up initial import before showing splash
    import logging

    from meshsee.logconfig import set_logging_level, setup_logging

    setup_logging()
    logger = logging.getLogger(__name__)
    set_logging_level()

    from meshsee.ui.splash import start_splash_process

    splash_conn = start_splash_process()
    from meshsee.app import main

    main(splash_conn)
