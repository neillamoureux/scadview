def main():
    # Load modules only when needed to speed up initial import before showing splash

    import sys

    from scadview.debug_info import create_debug_info_service
    from scadview.logging_main import (
        DEFAULT_LOG_LEVEL,
        configure_logging,
        parse_logging_level,
    )

    configure_logging(DEFAULT_LOG_LEVEL)
    args = parse_logging_level()
    debug_info_service = create_debug_info_service(
        sys.argv[1:],
        args.debug_info_file,
        args.debug_info_redact_sensitive,
    )

    from scadview.ui.splash import start_splash_process

    splash_conn = start_splash_process()
    from scadview.app import main

    main(splash_conn, debug_info_service)


if __name__ == "__main__":
    main()
