def main():
    # Load modules only when needed to speed up initial import before showing splash

    from scadview.logging_main import (
        DEFAULT_LOG_LEVEL,
        configure_logging,
        parse_logging_level,
    )

    configure_logging(DEFAULT_LOG_LEVEL)
    parse_logging_level()

    from scadview.ui.splash import start_splash_process

    splash_conn = start_splash_process()
    from scadview.app import main

    main(splash_conn)


if __name__ == "__main__":
    main()
