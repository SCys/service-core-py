import math
import os


def pretty_size(size_bytes):
    if size_bytes == 0:
        return "0B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def setup_autoreload(app):
    BLACK_LIST = ["data", "log"]
    WHITE_LIST = [".py", ".ini"]

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class ReloadEventHandler(FileSystemEventHandler):
            def __init__(self, app):
                super().__init__()

                self.app = app

            def on_modified(self, event):
                super().on_modified(event)

                app = self.app
                path = event.src_path

                items = os.path.split(path)
                if items[0] in BLACK_LIST:
                    return

                if not any([True for i in WHITE_LIST if items[1].endswith(i)]):
                    return

                what = "directory" if event.is_directory else "file"
                app.logger.info(f"Modified {what}: {path}")

                app.watchdog.stop()

                app.reload()

        event_handler = ReloadEventHandler(app)
        observer = Observer()
        observer.schedule(event_handler, ".", recursive=True)

        app.watchdog = observer

        observer.start()
    except ImportError:
        pass
