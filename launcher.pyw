#!/usr/bin/env python3
"""强势调整选股 — 启动器"""
import tkinter as tk, subprocess, sys, os, webbrowser, threading, http.server, socketserver, time, random, socket, json
from datetime import datetime

DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(DIR)
PORT = 8899
CACHE_FILE = os.path.join(DIR, 'scan_cache.json')

# ==================== 矩阵雨 ====================
class MatrixCanvas(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg='#0a0a0a', highlightthickness=0, **kw)
        self.chars = '小然拆解'
        self.drops = []; self.running = True
        self.after(50, self._init_drops)
    def _init_drops(self):
        w = self.winfo_width() or 560; fs = 48
        cols = max(4, w // fs)
        self.drops = [{'x': c*fs + 24, 'y': random.randint(-700, 0), 's': 2+random.random()*5} for c in range(cols)]
        self._draw()
    def _draw(self):
        if not self.running: return
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2 or h < 2: self.after(60, self._draw); return
        self.delete('all')
        colors = ['#ffd970', '#f2c24f', '#e0ab3d', '#c99a30']
        for d in self.drops:
            d['y'] += d['s']
            if d['y'] > h + 40: d['y'] = random.randint(-300, -20); d['s'] = 2+random.random()*5
            for j, ch in enumerate(self.chars):
                cy = d['y'] + j*24
                if cy < -24 or cy > h + 24: continue
                self.create_text(d['x'], cy, text=ch, fill=colors[j], font=('Microsoft YaHei UI', 15), anchor='n')
        self.after(50, self._draw)
    def stop(self): self.running = False

# ==================== 主窗口 ====================
class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('强势调整选股 · 启动器')
        self.geometry('560x620'); self.resizable(False, False); self.configure(bg='#0a0a0a')
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f'560x620+{(sw-560)//2}+{(sh-620)//2}')
        self._running = False; self._build()

    def _build(self):
        # 矩阵雨背景
        self.matrix = MatrixCanvas(self)
        self.matrix.place(x=0, y=0, relwidth=1, relheight=1)

        # 覆盖层
        f = tk.Frame(self, bg='#0a0a0a')
        f.place(relx=0.5, rely=0.5, anchor='center', width=500, height=570)

        # 标题
        tf = tk.Frame(f, bg='#0a0a0a'); tf.pack(pady=(14, 8))
        tk.Label(tf, text='◆ 强 势 调 整 选 股 ◆', font=('Microsoft YaHei UI', 20, 'bold'), fg='#ffd970', bg='#0a0a0a').pack()
        tk.Label(tf, text='STRONG ADJUSTMENT STOCK SCREENER', font=('Consolas', 9), fg='#c9a34a', bg='#0a0a0a').pack()
        tk.Label(tf, text='baostock · 全A股实时扫描', font=('Microsoft YaHei UI', 8), fg='#6b6448', bg='#0a0a0a').pack(pady=(2, 0))

        sep = tk.Frame(f, bg='#c9a34a', height=1); sep.pack(fill='x', padx=20, pady=6)

        # 板块选择
        tk.Label(f, text='▸ 板块选择', font=('Microsoft YaHei UI', 12, 'bold'), fg='#ffd970', bg='#0a0a0a').pack(anchor='w', padx=30)
        cf = tk.Frame(f, bg='#0a0a0a'); cf.pack(fill='x', padx=40, pady=4)
        cb = {'bg': '#0a0a0a', 'fg': '#e0dcc8', 'selectcolor': '#0a0a0a', 'activebackground': '#0a0a0a', 'activeforeground': '#ffd970', 'font': ('Microsoft YaHei UI', 11)}
        self.v_cy = tk.BooleanVar(value=False); self.v_sx = tk.BooleanVar(value=False); self.v_st = tk.BooleanVar(value=False)
        tk.Checkbutton(cf, text='创业板 (300/301)', variable=self.v_cy, **cb).grid(row=0, column=0, sticky='w', padx=(0, 30), pady=2)
        tk.Checkbutton(cf, text='科创板 (688)', variable=self.v_sx, **cb).grid(row=0, column=1, sticky='w', padx=(0, 30), pady=2)
        tk.Checkbutton(cf, text='ST 股票', variable=self.v_st, **cb).grid(row=1, column=0, sticky='w', pady=2)

        sep2 = tk.Frame(f, bg='#c9a34a', height=1); sep2.pack(fill='x', padx=20, pady=8)

        # 换手率
        tk.Label(f, text='▸ 换手率 (%)', font=('Microsoft YaHei UI', 12, 'bold'), fg='#ffd970', bg='#0a0a0a').pack(anchor='w', padx=30)
        tuf = tk.Frame(f, bg='#0a0a0a'); tuf.pack(fill='x', padx=30, pady=4)
        tk.Label(tuf, text='最低', fg='#e0dcc8', bg='#0a0a0a', font=('Microsoft YaHei UI', 10)).pack(side='left')
        self.s_min = tk.Scale(tuf, from_=0, to=20, resolution=0.5, orient='horizontal', length=160, bg='#111118', fg='#ffd970', troughcolor='#1a1a10', highlightthickness=0, activebackground='#c9a34a', font=('Consolas', 8)); self.s_min.set(1); self.s_min.pack(side='left', padx=(4, 20))
        tk.Label(tuf, text='最高', fg='#e0dcc8', bg='#0a0a0a', font=('Microsoft YaHei UI', 10)).pack(side='left')
        self.s_max = tk.Scale(tuf, from_=5, to=100, resolution=1, orient='horizontal', length=160, bg='#111118', fg='#ffd970', troughcolor='#1a1a10', highlightthickness=0, activebackground='#c9a34a', font=('Consolas', 8)); self.s_max.set(30); self.s_max.pack(side='left', padx=(4, 0))

        sep3 = tk.Frame(f, bg='#c9a34a', height=1); sep3.pack(fill='x', padx=20, pady=8)

        # 成交额
        tk.Label(f, text='▸ 最低成交额 (万元)', font=('Microsoft YaHei UI', 12, 'bold'), fg='#ffd970', bg='#0a0a0a').pack(anchor='w', padx=30)
        amf = tk.Frame(f, bg='#0a0a0a'); amf.pack(fill='x', padx=30, pady=4)
        tk.Label(amf, text='≥', fg='#e0dcc8', bg='#0a0a0a', font=('Microsoft YaHei UI', 10)).pack(side='left')
        self.s_amt = tk.Scale(amf, from_=0, to=50000, resolution=500, orient='horizontal', length=380, bg='#111118', fg='#ffd970', troughcolor='#1a1a10', highlightthickness=0, activebackground='#c9a34a', font=('Consolas', 8)); self.s_amt.set(3000); self.s_amt.pack(side='left', padx=(4, 0))

        # 进度条
        self.pbar = tk.Canvas(f, width=400, height=6, bg='#111118', highlightthickness=0)
        self.pbar.pack(pady=(0, 8))

        # 启动按钮
        bf = tk.Frame(f, bg='#0a0a0a'); bf.pack(pady=8)
        self.btn = tk.Button(bf, text='▶  启 动 扫 描', command=self._launch, font=('Microsoft YaHei UI', 15, 'bold'), fg='#0a0a0a', bg='#ffd970', activeforeground='#0a0a0a', activebackground='#e0ab3d', relief='flat', cursor='hand2', padx=48, pady=10, borderwidth=0); self.btn.pack()

        # 状态
        self.status = tk.StringVar(value='就绪 · 等待启动')
        tk.Label(f, textvariable=self.status, font=('Microsoft YaHei UI', 9), fg='#6b6448', bg='#0a0a0a').pack(pady=(6, 0))

        # 预计耗时提示
        tk.Label(f, text='扫描预计 30~40 分钟', font=('Microsoft YaHei UI', 9), fg='#c9a34a', bg='#0a0a0a').pack(pady=(4, 0))

        # 作者署名（右下角）
        tk.Label(self, text='作者:小然拆解', font=('Microsoft YaHei UI', 13, 'bold'), fg='#ffd970', bg='#0a0a0a').place(relx=1.0, rely=1.0, anchor='se', x=-14, y=-10)

        self._pbar_val = 0  # 进度 0.0 ~ 1.0

    def _params_str(self, cmd):
        """提取筛选参数（去掉 python 路径和脚本名）"""
        return ' '.join(cmd[2:] if len(cmd) > 2 else cmd[1:])

    def _can_skip_scan(self, cmd):
        """检查是否可以跳过扫描直接使用当日缓存"""
        now = datetime.now()
        # 检查缓存文件
        if not os.path.exists(CACHE_FILE):
            return False
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except:
            return False
        # 参数必须一致
        if cache.get('params', '') != self._params_str(cmd):
            return False
        # 缓存必须是今天生成的
        if cache.get('date', '') != now.strftime('%Y-%m-%d'):
            return False
        # 结果文件必须存在
        if not os.path.exists('scan_result.json'):
            return False
        # 缓存是收盘前生成的，而现在已收盘 → 允许重扫一次，拿到当天最终数据
        if not cache.get('post_close', False) and now.hour >= 15:
            return False
        return True

    def _save_cache(self, cmd):
        """扫描成功后保存参数缓存"""
        now = datetime.now()
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'params': self._params_str(cmd),
                    'date': now.strftime('%Y-%m-%d'),
                    'time': now.strftime('%H:%M:%S'),
                    'post_close': now.hour >= 15,
                }, f)
        except:
            pass

    def _set_progress(self, val):
        """更新进度条 0.0 ~ 1.0"""
        self._pbar_val = max(self._pbar_val, val)
        w = 400 * self._pbar_val
        self.pbar.delete('all')
        self.pbar.create_rectangle(0, 0, w, 6, fill='#ffd970', outline='')
        if self._pbar_val > 0.01:
            self.pbar.create_text(w-8 if w>30 else w+12, 3, text=f'{int(self._pbar_val*100)}%', fill='#0a0a0a' if w>30 else '#ffd970', font=('Consolas', 7))

    def _launch(self):
        if self._running: return
        self._running = True

        cmd = [sys.executable, 'scanner_engine.py']
        if self.v_cy.get(): cmd.append('--include-chinext')
        if self.v_sx.get(): cmd.append('--include-star')
        if self.v_st.get(): cmd.append('--include-st')
        cmd.extend(['--min-turnover', str(self.s_min.get())])
        cmd.extend(['--max-turnover', str(self.s_max.get())])
        cmd.extend(['--min-amount', str(self.s_amt.get())])

        # === 收盘后缓存复用 ===
        if self._can_skip_scan(cmd):
            self.status.set('使用当日缓存结果')
            self._set_progress(1.0)
            self.btn.config(text='✓ 已加载', state='normal', bg='#00b894', fg='#fff')
            # 直接启动 HTTP 服务 → 打开浏览器
            class H(http.server.SimpleHTTPRequestHandler):
                def log_message(self, f, *a): pass
            srv = socketserver.TCPServer(('127.0.0.1', PORT), H)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            webbrowser.open(f'http://127.0.0.1:{PORT}/index.html')
            self.after(3000, lambda: self.status.set(f'缓存加载 · http://127.0.0.1:{PORT}'))
            self.after(5000, lambda: self.btn.config(text='▶  启 动 扫 描', state='normal', bg='#ffd970', fg='#0a0a0a'))
            self._running = False
            return

        self.btn.config(text='⏳ 扫描中...', state='disabled', bg='#c9a34a', activebackground='#c9a34a')
        self.status.set('检测数据源连通性...')
        self._pbar_val = 0; self._set_progress(0)

        def run():
            import re
            env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
            total_stocks = 0

            # 快速检测 baostock 连通性（实际数据端口是 10030）
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect(('public-api.baostock.com', 10030))
                sock.close()
            except Exception as e:
                self.after(0, lambda: self.status.set(f'数据源不可达: {e}'))
                self.after(0, lambda: self.btn.config(text='▶  重 试', state='normal', bg='#ffd970', fg='#0a0a0a'))
                self._running = False; return

            self.after(0, lambda: self.status.set('正在扫描 A 股，请稍候...'))
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', env=env)
                for line in proc.stdout:
                    line = line.strip()
                    if not line: continue

                    # 解析总数: "获取到 200 只股票" 或 "获取到 5000 只股票，开始扫描..."
                    m = re.search(r'获取到\s*(\d+)\s*只', line)
                    if m and not total_stocks:
                        total_stocks = int(m.group(1))

                    # 解析实时进度: "扫描中 100/200"
                    for part in line.split('\r'):
                        part = part.strip()
                        m2 = re.search(r'扫描中\s*(\d+)/(\d+)', part)
                        if m2:
                            cur, tot = int(m2.group(1)), int(m2.group(2))
                            if tot > 0:
                                if not total_stocks: total_stocks = tot
                                self.after(0, lambda c=cur: self._set_progress(c / total_stocks if total_stocks else 0))
                            break  # 取最后一个进度

                    # 状态文本
                    if '★' in line or '扫描完成' in line or '报错' in line or '过滤' in line:
                        self.after(0, lambda l=line: self.status.set(l[:80]))

                proc.wait()
                self.after(0, lambda: self._set_progress(1.0))
                if proc.returncode == 0:
                    self._save_cache(cmd)
            except Exception as e:
                self.after(0, lambda: self.status.set(f'扫描失败: {e}'))
                self.after(0, lambda: self.btn.config(text='▶  重 试', state='normal', bg='#ffd970', fg='#0a0a0a'))
                self._running = False; return

            # 扫描完成 → 启动 HTTP 服务 → 打开浏览器
            self.after(0, lambda: self.status.set('扫描完成 · 正在打开浏览器...'))
            self.after(0, lambda: self.btn.config(text='✓ 完成', state='normal', bg='#00b894', fg='#fff'))

            class H(http.server.SimpleHTTPRequestHandler):
                def log_message(self, f, *a): pass
            srv = socketserver.TCPServer(('127.0.0.1', PORT), H)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            webbrowser.open(f'http://127.0.0.1:{PORT}/index.html')
            self.after(3000, lambda: self.status.set(f'浏览器已打开 · http://127.0.0.1:{PORT}'))
            self.after(5000, lambda: self.btn.config(text='▶  启 动 扫 描', state='normal', bg='#ffd970', fg='#0a0a0a'))
            self._running = False

        threading.Thread(target=run, daemon=True).start()

    def destroy(self):
        if hasattr(self, 'matrix'): self.matrix.stop()
        super().destroy()

if __name__ == '__main__':
    Launcher().mainloop()
