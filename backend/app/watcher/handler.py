from watchdog.events import FileSystemEventHandler

class WatcherHandler(FileSystemEventHandler):
    def __init__(self, task_func, task_id):
        super().__init__()
        self.task_func = task_func
        self.task_id = task_id

    def on_created(self, event):
        if not event.is_directory:
            print(f"文件新增: {event.src_path}, 任务ID: {self.task_id}")
            self.task_func(self.task_id)

    def on_modified(self, event):
        if not event.is_directory:
            print(f"文件修改: {event.src_path}, 任务ID: {self.task_id}")
            self.task_func(self.task_id)

    def on_deleted(self, event):
        if not event.is_directory:
            print(f"文件删除: {event.src_path}, 任务ID: {self.task_id}")
            self.task_func(self.task_id)
    
    def on_moved(self, event):
        if not event.is_directory:
            print(f"文件移动: {event.src_path} -> {event.dest_path}, 任务ID: {self.task_id}")
            self.task_func(self.task_id)
