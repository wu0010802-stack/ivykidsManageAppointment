from ivykids_monitor import IvykidsMonitor

if __name__ == "__main__":
    monitor = IvykidsMonitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        pass
