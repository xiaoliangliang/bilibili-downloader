import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
import re

# Import our downloader class
from bilibili_downloader import BilibiliDownloader

class BilibiliDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bilibili 视频下载器")
        self.root.geometry("700x400")  # 增大窗口以容纳新控件
        self.root.resizable(True, True)
        
        # 默认不使用cookie
        self.downloader = BilibiliDownloader()
        self.setup_ui()
        
    def setup_ui(self):
        # URL input
        url_frame = ttk.Frame(self.root, padding="10")
        url_frame.pack(fill=tk.X)
        
        ttk.Label(url_frame, text="B站视频链接:").pack(side=tk.LEFT)
        self.url_var = tk.StringVar()
        ttk.Entry(url_frame, textvariable=self.url_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Output directory selection
        dir_frame = ttk.Frame(self.root, padding="10")
        dir_frame.pack(fill=tk.X)
        
        ttk.Label(dir_frame, text="保存位置:").pack(side=tk.LEFT)
        self.dir_var = tk.StringVar(value="D:\\projects\\blibli\\output")
        ttk.Entry(dir_frame, textvariable=self.dir_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="浏览...", command=self.browse_directory).pack(side=tk.LEFT)
        
        # 添加Cookie输入框
        cookie_frame = ttk.Frame(self.root, padding="10")
        cookie_frame.pack(fill=tk.X)
        
        ttk.Label(cookie_frame, text="Cookie (可选):").pack(side=tk.LEFT)
        self.cookie_var = tk.StringVar()
        ttk.Entry(cookie_frame, textvariable=self.cookie_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 添加清晰度选择
        quality_frame = ttk.Frame(self.root, padding="10")
        quality_frame.pack(fill=tk.X)
        
        ttk.Label(quality_frame, text="视频清晰度:").pack(side=tk.LEFT)
        self.quality_var = tk.StringVar(value="120")
        
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.quality_var, width=20)
        quality_combo['values'] = (
            "4K (120)", 
            "1080P 60帧 (116)", 
            "1080P+ (112)", 
            "1080P (80)", 
            "720P 60帧 (74)", 
            "720P (64)",
            "480P (32)",
            "360P (16)"
        )
        quality_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(quality_frame, text="(大会员可用更高清晰度)").pack(side=tk.LEFT)
        
        # Download button
        btn_frame = ttk.Frame(self.root, padding="10")
        btn_frame.pack(fill=tk.X)
        
        self.download_btn = ttk.Button(btn_frame, text="下载视频", command=self.start_download)
        self.download_btn.pack(pady=10)
        
        # Progress bar and status
        progress_frame = ttk.Frame(self.root, padding="10")
        progress_frame.pack(fill=tk.X)
        
        self.status_var = tk.StringVar(value="准备就绪")
        ttk.Label(progress_frame, textvariable=self.status_var).pack(fill=tk.X)
        
        self.progress = ttk.Progressbar(progress_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=5)
        
    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.dir_var.get())
        if directory:
            self.dir_var.set(directory)
    
    def start_download(self):
        url = self.url_var.get().strip()
        output_dir = self.dir_var.get().strip()
        cookie = self.cookie_var.get().strip()
        
        # 提取清晰度数字
        quality_text = self.quality_var.get()
        quality = 120  # 默认值
        match = re.search(r'\((\d+)\)', quality_text)
        if match:
            quality = int(match.group(1))
        
        if not url:
            messagebox.showerror("错误", "请输入B站视频链接")
            return
        
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir)
            except:
                messagebox.showerror("错误", f"无法创建目录: {output_dir}")
                return
        
        # Disable UI during download
        self.download_btn.config(state="disabled")
        self.progress.start()
        self.status_var.set("正在下载，请稍候...")
        
        # 重新创建下载器以使用cookie
        if cookie:
            self.downloader = BilibiliDownloader(cookies=cookie)
        else:
            self.downloader = BilibiliDownloader()
        
        # Start download in a separate thread
        thread = Thread(target=self.download_thread, args=(url, output_dir))
        thread.daemon = True
        thread.start()
    
    def download_thread(self, url, output_dir):
        try:
            # 提取清晰度数字
            quality_text = self.quality_var.get()
            quality = 120  # 默认值
            match = re.search(r'\((\d+)\)', quality_text)
            if match:
                quality = int(match.group(1))
                
            output_path = self.downloader.download_video(url, output_dir, quality)
            
            # Update UI in the main thread
            self.root.after(0, self.download_complete, output_path)
        except Exception as e:
            # Update UI in the main thread
            self.root.after(0, self.download_error, str(e))
    
    def download_complete(self, output_path):
        self.progress.stop()
        self.download_btn.config(state="normal")
        self.status_var.set(f"下载完成: {output_path}")
        
        if messagebox.askyesno("下载完成", f"视频已下载到: {output_path}\n\n是否打开所在文件夹?"):
            self.open_file_location(output_path)
    
    def download_error(self, error_msg):
        self.progress.stop()
        self.download_btn.config(state="normal")
        self.status_var.set(f"下载失败: {error_msg}")
        messagebox.showerror("下载失败", f"错误信息: {error_msg}")
    
    def open_file_location(self, file_path):
        """Open the folder containing the file"""
        folder_path = os.path.dirname(os.path.abspath(file_path))
        if sys.platform == 'win32':
            os.startfile(folder_path)
        elif sys.platform == 'darwin':  # macOS
            os.system(f'open "{folder_path}"')
        else:  # Linux
            os.system(f'xdg-open "{folder_path}"')

if __name__ == "__main__":
    root = tk.Tk()
    app = BilibiliDownloaderGUI(root)
    root.mainloop()