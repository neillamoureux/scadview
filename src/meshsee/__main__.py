
if __name__ == "__main__":
    # Load modules only when needed to speed up initial import before showing splash
    from meshsee.ui.splash import start_splash_process
    splash_conn = start_splash_process()
    from meshsee.app import main
    main(splash_conn)
