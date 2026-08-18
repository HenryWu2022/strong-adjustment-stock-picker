#!/usr/bin/env python3
"""强势调整选股系统 — 桌面版 (tkinter GUI)
双击此文件即可运行，或在命令行执行: pythonw stock_picker_gui.pyw
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
import os
import sys
import webbrowser
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner_engine import run_scan, screen, get_stock_list

RESULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scan_result.json')

# ===================== 配色方案 (暗色主题) =====================
COLORS = {
    'bg': '#0d1117',
    'bg2': '#161b22',
    'bg3': '#1c2333',
    'border': '#30363d',
    'text': '#e6edf3',
    'text2': '#8b949e',
    'text3': '#6e7681',
    'red': '#e94560',
    'green': '#00b894',
    'orange': '#f59e0b',
    'blue': '#58a6ff',
    'gold': '#d4a853',
    'purple': '#a855f7',
}


class StockPickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title('强势调整选股系统 v4')
        self.root.geometry('1200x800')
        self.root.minsize(900, 600)

        # 设置图标（如果有的话）
        self.root.configure(bg=COLORS['bg'])

        # 状态
        self.scanning = False
        self.results = []
        self.sort_column = 'totalScore'
        self.sort_reverse = True

        # 样式
        self._setup_styles()

        # 构建 UI
        self._build_header()
        self._build_controls()
        self._build_table()
        self._build_statusbar()

        # 窗口居中
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f'{w}x{h}+{x}+{y}')

        # 绑定事件
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    # ===================== 样式 =====================

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        # 全局配置
        style.configure('.',
                        background=COLORS['bg'],
                        foreground=COLORS['text'],
                        fieldbackground=COLORS['bg2'],
                        borderwidth=0,
                        font=('Microsoft YaHei UI', 10))

        # 按钮样式
        style.configure('Primary.TButton',
                        background=COLORS['green'],
                        foreground='white',
                        padding=(24, 10),
                        font=('Microsoft YaHei UI', 11, 'bold'),
                        borderwidth=0)
        style.map('Primary.TButton',
                  background=[('active', '#00c49a'), ('disabled', COLORS['border'])])

        style.configure('Secondary.TButton',
                        background=COLORS['bg3'],
                        foreground=COLORS['text'],
                        padding=(12, 6),
                        borderwidth=1)
        style.map('Secondary.TButton',
                  background=[('active', COLORS['border'])])

        # 标签框
        style.configure('Card.TLabelframe',
                        background=COLORS['bg2'],
                        bordercolor=COLORS['border'],
                        relief='solid',
                        borderwidth=1)
        style.configure('Card.TLabelframe.Label',
                        background=COLORS['bg2'],
                        foreground=COLORS['text2'],
                        font=('Microsoft YaHei UI', 9))

        # 进度条
        style.configure('TProgressbar',
                        background=COLORS['green'],
                        troughcolor=COLORS['bg3'],
                        borderwidth=0,
                        thickness=8)

        # Treeview
        style.configure('Treeview',
                        background=COLORS['bg2'],
                        foreground=COLORS['text'],
                        fieldbackground=COLORS['bg2'],
                        borderwidth=0,
                        rowheight=36,
                        font=('Consolas', 10))
        style.configure('Treeview.Heading',
                        background=COLORS['bg3'],
                        foreground=COLORS['text'],
                        font=('Microsoft YaHei UI', 10, 'bold'),
                        padding=(8, 6),
                        borderwidth=0)
        style.map('Treeview',
                  background=[('selected', COLORS['blue'])],
                  foreground=[('selected', 'white')])
        style.map('Treeview.Heading',
                  background=[('active', COLORS['border'])])

        # 滚动条
        style.configure('TScrollbar',
                        background=COLORS['bg3'],
                        troughcolor=COLORS['bg'],
                        borderwidth=0,
                        arrowsize=14)

    # ===================== 头部 =====================

    def _build_header(self):
        header = tk.Frame(self.root, bg='#1a1a3e', height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        inner = tk.Frame(header, bg='#1a1a3e')
        inner.pack(fill=tk.BOTH, expand=True, padx=20)

        title = tk.Label(inner,
                         text='强势调整选股系统',
                         font=('Microsoft YaHei UI', 20, 'bold'),
                         fg=COLORS['text'],
                         bg='#1a1a3e')
        title.pack(side=tk.LEFT, pady=12)

        version = tk.Label(inner,
                           text='v4 · baostock 数据源',
                           font=('Microsoft YaHei UI', 10),
                           fg=COLORS['text2'],
                           bg='#1a1a3e')
        version.pack(side=tk.LEFT, padx=(8, 0), pady=16)

        time_label = tk.Label(inner,
                              text=datetime.now().strftime('%Y-%m-%d %H:%M'),
                              font=('Microsoft YaHei UI', 10),
                              fg=COLORS['text3'],
                              bg='#1a1a3e')
        time_label.pack(side=tk.RIGHT, pady=16)
        self.time_label = time_label

    # ===================== 控制栏 =====================

    def _build_controls(self):
        ctrl = tk.Frame(self.root, bg=COLORS['bg2'], height=70)
        ctrl.pack(fill=tk.X)
        ctrl.pack_propagate(False)

        inner = tk.Frame(ctrl, bg=COLORS['bg2'])
        inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=12)

        # 市场过滤
        tk.Label(inner, text='市场:', fg=COLORS['text2'], bg=COLORS['bg2'],
                 font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT, padx=(0, 4))

        self.market_var = tk.StringVar(value='all')
        market_cb = ttk.Combobox(inner, textvariable=self.market_var,
                                 values=['全部A股', '主板', '创业板', '科创板'],
                                 state='readonly', width=8)
        market_cb.pack(side=tk.LEFT, padx=(0, 16))
        market_cb.bind('<<ComboboxSelected>>', lambda e: self._on_filter_change())

        # 排除ST
        self.exclude_st_var = tk.BooleanVar(value=True)
        st_cb = tk.Checkbutton(inner, text='排除ST', variable=self.exclude_st_var,
                               fg=COLORS['text2'], bg=COLORS['bg2'],
                               selectcolor=COLORS['bg3'],
                               activebackground=COLORS['bg2'],
                               activeforeground=COLORS['text'],
                               font=('Microsoft YaHei UI', 10))
        st_cb.pack(side=tk.LEFT, padx=(0, 16))

        # 扫描数量
        tk.Label(inner, text='扫描数量:', fg=COLORS['text2'], bg=COLORS['bg2'],
                 font=('Microsoft YaHei UI', 10)).pack(side=tk.LEFT, padx=(0, 4))

        self.limit_var = tk.StringVar(value='全部')
        limit_cb = ttk.Combobox(inner, textvariable=self.limit_var,
                                values=['全部', '100', '300', '500', '1000', '2000'],
                                state='readonly', width=6)
        limit_cb.pack(side=tk.LEFT, padx=(0, 20))

        # 扫描按钮
        self.scan_btn = tk.Button(inner, text='▶  开始扫描', command=self._start_scan,
                                  bg=COLORS['green'], fg='white',
                                  font=('Microsoft YaHei UI', 11, 'bold'),
                                  relief=tk.FLAT, cursor='hand2',
                                  padx=24, pady=8,
                                  activebackground='#00c49a', activeforeground='white')
        self.scan_btn.pack(side=tk.LEFT, padx=(0, 12))

        # 停止按钮
        self.stop_btn = tk.Button(inner, text='■ 停止', command=self._stop_scan,
                                  bg=COLORS['red'], fg='white',
                                  font=('Microsoft YaHei UI', 11, 'bold'),
                                  relief=tk.FLAT, cursor='hand2',
                                  padx=16, pady=8,
                                  activebackground=COLORS['red'], activeforeground='white',
                                  state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 20))

        # 导出按钮
        self.export_btn = tk.Button(inner, text='📄 导出JSON', command=self._export_json,
                                    bg=COLORS['bg3'], fg=COLORS['text'],
                                    font=('Microsoft YaHei UI', 10),
                                    relief=tk.FLAT, cursor='hand2',
                                    padx=14, pady=8,
                                    activebackground=COLORS['border'], activeforeground=COLORS['text'])
        self.export_btn.pack(side=tk.LEFT, padx=(0, 12))

        # 查看HTML按钮
        self.html_btn = tk.Button(inner, text='🌐 打开HTML', command=self._open_html,
                                  bg=COLORS['bg3'], fg=COLORS['text'],
                                  font=('Microsoft YaHei UI', 10),
                                  relief=tk.FLAT, cursor='hand2',
                                  padx=14, pady=8,
                                  activebackground=COLORS['border'], activeforeground=COLORS['text'])
        self.html_btn.pack(side=tk.LEFT)

    # ===================== 表格主区域 =====================

    def _build_table(self):
        # 表格卡片
        table_frame = tk.Frame(self.root, bg=COLORS['bg'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 4))

        # 工具栏：进度信息 + 结果统计
        toolbar = tk.Frame(table_frame, bg=COLORS['bg'])
        toolbar.pack(fill=tk.X, pady=(0, 4))

        self.progress_label = tk.Label(toolbar,
                                       text='就绪，点击"开始扫描"',
                                       fg=COLORS['text2'], bg=COLORS['bg'],
                                       font=('Microsoft YaHei UI', 10))
        self.progress_label.pack(side=tk.LEFT)

        self.stats_label = tk.Label(toolbar,
                                    text='',
                                    fg=COLORS['gold'], bg=COLORS['bg'],
                                    font=('Microsoft YaHei UI', 10))
        self.stats_label.pack(side=tk.RIGHT)

        # 进度条
        self.progress_bar = ttk.Progressbar(table_frame, mode='determinate', style='TProgressbar')
        self.progress_bar.pack(fill=tk.X, pady=(0, 6))

        # 表格容器
        tree_container = tk.Frame(table_frame, bg=COLORS['bg2'])
        tree_container.pack(fill=tk.BOTH, expand=True)

        # 列定义
        columns = ('code', 'name', 'board', 'price', 'change', 'score',
                   'trigger_date', 'buy_date', 'buy_price', 'stop_loss', 'risk', 'status')

        self.tree = ttk.Treeview(tree_container, columns=columns,
                                 show='headings', selectmode='browse')

        # 列标题与配置
        col_config = {
            'code': ('代码', 80),
            'name': ('名称', 100),
            'board': ('板块', 60),
            'price': ('现价', 75),
            'change': ('涨跌幅%', 75),
            'score': ('评分', 55),
            'trigger_date': ('涨停日', 95),
            'buy_date': ('买点日', 95),
            'buy_price': ('买价', 75),
            'stop_loss': ('止损价', 75),
            'risk': ('风险%', 70),
            'status': ('状态', 70),
        }

        for col, (title, width) in col_config.items():
            self.tree.heading(col, text=title,
                              command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=width, minwidth=width // 2,
                             anchor='center')

        # 特殊对齐
        self.tree.column('name', anchor='w')

        # 滚动条
        vsb = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # 双击查看详情
        self.tree.bind('<Double-1>', self._show_detail)

        # 右键菜单
        self.tree.bind('<Button-3>', self._right_click_menu)

    # ===================== 状态栏 =====================

    def _build_statusbar(self):
        status = tk.Frame(self.root, bg=COLORS['bg2'], height=28)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        status.pack_propagate(False)

        self.status_text = tk.Label(status,
                                    text='数据源: baostock | 免费开源，无需注册',
                                    fg=COLORS['text3'], bg=COLORS['bg2'],
                                    font=('Microsoft YaHei UI', 8))
        self.status_text.pack(side=tk.LEFT, padx=12, pady=4)

        self.status_count = tk.Label(status,
                                     text='',
                                     fg=COLORS['text3'], bg=COLORS['bg2'],
                                     font=('Microsoft YaHei UI', 8))
        self.status_count.pack(side=tk.RIGHT, padx=12, pady=4)

    # ===================== 右键菜单 =====================

    def _right_click_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)

        menu = tk.Menu(self.root, tearoff=0,
                       bg=COLORS['bg2'], fg=COLORS['text'],
                       activebackground=COLORS['blue'],
                       activeforeground='white',
                       font=('Microsoft YaHei UI', 10))
        menu.add_command(label='查看详情', command=lambda: self._show_detail(None))
        menu.add_command(label='复制代码', command=self._copy_code)
        menu.post(event.x_root, event.y_root)

    def _copy_code(self):
        sel = self.tree.selection()
        if sel:
            code = self.tree.item(sel[0], 'values')[0]
            self.root.clipboard_clear()
            self.root.clipboard_append(code)
            self._set_status(f'已复制: {code}')

    # ===================== 扫描逻辑 =====================

    def _start_scan(self):
        if self.scanning:
            return

        self.scanning = True
        self.scan_btn.config(state=tk.DISABLED, text='⏳ 扫描中...')
        self.stop_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.DISABLED)

        # 清空旧结果
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results = []
        self.progress_bar['value'] = 0
        self.stats_label.config(text='')

        # 解析过滤参数
        market_map = {
            '全部A股': 'all', '主板': '主板', '创业板': '创业板',
            '科创板': '科创板',
        }
        market_filter = market_map.get(self.market_var.get(), 'all')
        exclude_st = self.exclude_st_var.get()
        limit_str = self.limit_var.get()
        max_stocks = None if limit_str == '全部' else int(limit_str)

        # 停止事件
        self._stop_event = threading.Event()

        # 在新线程中运行扫描
        thread = threading.Thread(target=self._run_scan_thread,
                                  args=(exclude_st, market_filter, max_stocks, self._stop_event),
                                  daemon=True)
        thread.start()

    def _run_scan_thread(self, exclude_st, market_filter, max_stocks, stop_event):
        try:
            results, total = run_scan(
                exclude_st=exclude_st,
                market_filter=market_filter,
                max_stocks=max_stocks,
                progress_callback=self._on_progress,
                stop_event=stop_event,
            )
            self.results = results
            self.root.after(0, self._on_scan_done, results, total)
        except Exception as e:
            self.root.after(0, self._on_scan_error, str(e))

    def _on_progress(self, phase, cur, total, msg):
        """进度回调（在工作线程中调用，需要 after）"""
        def update():
            if total > 0:
                self.progress_bar['maximum'] = total
                self.progress_bar['value'] = cur
            self.progress_label.config(text=msg)
            self._update_time()

        self.root.after(0, update)

    def _populate_table(self):
        """填充结果表格"""
        # 清除现有行
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 添加标签
        self.tree.tag_configure('has_buy', foreground=COLORS['green'])
        self.tree.tag_configure('no_buy', foreground=COLORS['text2'])
        self.tree.tag_configure('risk_high', foreground=COLORS['red'])

        for i, r in enumerate(self.results):
            pct_change = r.get('pctChange', 0)
            change_str = f"{pct_change:+.2f}" if isinstance(pct_change, (int, float)) else '--'

            buy_price_str = f"{r['buyPrice']:.2f}" if r.get('buyPrice') else '--'

            risk_pct = r.get('riskPct', 0) * 100
            risk_str = f"{risk_pct:.2f}"

            values = (
                r['code'],
                r['name'],
                r.get('board', '--'),
                f"{r['latestPrice']:.2f}",
                change_str,
                str(r['totalScore']),
                r['triggerLimitDate'],
                r['buySignalDate'] or '--',
                buy_price_str,
                f"{r['stopLoss']:.2f}",
                risk_str,
                r['status'],
            )

            tag = 'has_buy' if r['hasBuySignal'] else 'no_buy'
            if r.get('isStopBroken'):
                tag = 'risk_high'

            self.tree.insert('', tk.END, values=values, tags=(tag,), iid=str(i))

        self.status_count.config(text=f'共 {len(self.results)} 只候选')

    def _on_scan_done(self, results, total):
        """扫描完成"""
        self.scanning = False
        self.scan_btn.config(state=tk.NORMAL, text='▶  开始扫描')
        self.stop_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.NORMAL)
        self.progress_bar['value'] = total

        self._populate_table()

        match_count = len(results)
        self.stats_label.config(text=f'扫描 {total} 只 | 匹配 {match_count} 只 | 命中率 {match_count/total*100:.1f}%' if total > 0 else '')
        self._set_status(f'扫描完成：{match_count} 只符合强势调整条件')

        if match_count == 0:
            messagebox.showinfo('扫描结果', '没有符合条件的股票。\n可能是市场环境不佳，或筛选条件过严。')

    def _on_scan_error(self, error_msg):
        """扫描出错"""
        self.scanning = False
        self.scan_btn.config(state=tk.NORMAL, text='▶  开始扫描')
        self.stop_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.NORMAL)
        self._set_status(f'扫描出错: {error_msg}')
        messagebox.showerror('扫描错误', f'扫描过程中出现错误:\n\n{error_msg}\n\n请检查网络连接后重试。')

    def _stop_scan(self):
        """停止扫描"""
        if hasattr(self, '_stop_event'):
            self._stop_event.set()
        self.scanning = False
        self.scan_btn.config(state=tk.NORMAL, text='▶  开始扫描')
        self.stop_btn.config(state=tk.DISABLED)
        self._set_status('扫描已停止')
        self.progress_label.config(text='扫描已手动停止')

    # ===================== 详情弹窗 =====================

    def _show_detail(self, event):
        sel = self.tree.selection()
        if not sel:
            return

        idx = int(sel[0])
        if idx >= len(self.results):
            return

        r = self.results[idx]

        # 创建弹窗
        detail = tk.Toplevel(self.root)
        detail.title(f'{r["code"]} {r["name"]} - 详细信息')
        detail.geometry('600x700')
        detail.configure(bg=COLORS['bg'])
        detail.transient(self.root)

        # 内容
        content = tk.Frame(detail, bg=COLORS['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 标题
        title_frame = tk.Frame(content, bg=COLORS['bg'])
        title_frame.pack(fill=tk.X, pady=(0, 16))

        tk.Label(title_frame,
                 text=f'{r["code"]}  {r["name"]}',
                 font=('Microsoft YaHei UI', 18, 'bold'),
                 fg=COLORS['text'], bg=COLORS['bg']).pack(side=tk.LEFT)

        status_color = COLORS['green'] if r['hasBuySignal'] else COLORS['text2']
        tk.Label(title_frame,
                 text=r['status'],
                 font=('Microsoft YaHei UI', 12, 'bold'),
                 fg=status_color, bg=COLORS['bg']).pack(side=tk.RIGHT)

        # 基本信息
        info_frame = tk.Frame(content, bg=COLORS['bg2'])
        info_frame.pack(fill=tk.X, pady=(0, 12))

        info_items = [
            ('板块', r.get('board', '--')),
            ('现价', f"{r['latestPrice']:.2f}"),
            ('评分', str(r['totalScore'])),
            ('涨停日', r['triggerLimitDate']),
            ('买点日', r['buySignalDate'] or '未出现'),
            ('买价', f"{r['buyPrice']:.2f}" if r.get('buyPrice') else '--'),
            ('止损价', f"{r['stopLoss']:.2f}"),
            ('风险', f"{r.get('riskPct', 0) * 100:.2f}%"),
            ('止损状态', '已跌破' if r.get('isStopBroken') else '正常'),
        ]

        # 用简单的文本展示
        info_text = '\n'.join([f'{l}:  {v}' for l, v in info_items])
        tk.Label(info_frame, text=info_text,
                 font=('Consolas', 11), fg=COLORS['text'], bg=COLORS['bg2'],
                 justify=tk.LEFT, anchor='w').pack(fill=tk.X, padx=16, pady=12)

        # 评分明细
        score_label = tk.Label(content, text='📊 评分明细',
                               font=('Microsoft YaHei UI', 12, 'bold'),
                               fg=COLORS['text'], bg=COLORS['bg'])
        score_label.pack(anchor='w', pady=(8, 4))

        detail_frame = tk.Frame(content, bg=COLORS['bg2'])
        detail_frame.pack(fill=tk.BOTH, expand=True)

        detail_tree = ttk.Treeview(detail_frame,
                                   columns=('date', 'type', 'score', 'reason'),
                                   show='headings', height=10)
        detail_tree.heading('date', text='日期')
        detail_tree.heading('type', text='类型')
        detail_tree.heading('score', text='得分')
        detail_tree.heading('reason', text='原因')
        detail_tree.column('date', width=100, anchor='center')
        detail_tree.column('type', width=80, anchor='center')
        detail_tree.column('score', width=60, anchor='center')
        detail_tree.column('reason', width=200, anchor='w')

        detail_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        detail_vsb = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL,
                                   command=detail_tree.yview)
        detail_tree.configure(yscrollcommand=detail_vsb.set)
        detail_vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 颜色标签
        detail_tree.tag_configure('涨停', foreground=COLORS['red'])
        detail_tree.tag_configure('试盘线', foreground=COLORS['orange'])
        detail_tree.tag_configure('大阳线', foreground=COLORS['green'])

        for d in r.get('scoreDetails', []):
            detail_tree.insert('', tk.END,
                               values=(d['date'], d['type'], d['score'], d['reason']),
                               tags=(d['type'],))

        # 关闭按钮
        close_btn = tk.Button(content, text='关闭', command=detail.destroy,
                              bg=COLORS['bg3'], fg=COLORS['text'],
                              font=('Microsoft YaHei UI', 10),
                              relief=tk.FLAT, cursor='hand2',
                              padx=20, pady=6,
                              activebackground=COLORS['border'],
                              activeforeground=COLORS['text'])
        close_btn.pack(pady=(12, 0))

        detail.wait_window()

    # ===================== 排序 =====================

    def _sort_by(self, column):
        col_map = {
            'code': 'code', 'name': 'name', 'board': 'board',
            'price': 'latestPrice', 'change': 'pctChange',
            'score': 'totalScore', 'trigger_date': 'triggerLimitDate',
            'buy_date': 'buySignalDate', 'buy_price': 'buyPrice',
            'stop_loss': 'stopLoss', 'risk': 'riskPct', 'status': 'status',
        }

        key = col_map.get(column)
        if not key:
            return

        if self.sort_column == key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = key
            self.sort_reverse = (key == 'totalScore')  # 评分默认降序

        if self.sort_reverse:
            self.results.sort(key=lambda x: (
                -(x.get(key, 0) if isinstance(x.get(key), (int, float)) else 0),
                str(x.get(key, '')).lower()
            ))
        else:
            self.results.sort(key=lambda x: (
                x.get(key, 0) if isinstance(x.get(key), (int, float)) else 0,
                str(x.get(key, '')).lower()
            ))

        self._populate_table()

    # ===================== 导出 =====================

    def _export_json(self):
        if not self.results:
            messagebox.showinfo('提示', '没有结果可导出。')
            return

        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension='.json',
            filetypes=[('JSON 文件', '*.json')],
            initialfile=f'选股结果_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
        )
        if not path:
            return

        try:
            export_data = []
            for r in self.results:
                d = {k: v for k, v in r.items() if k != 'kline'}
                d['kline'] = r.get('kline', [])[-10:]  # 只保留最近10条
                export_data.append(d)

            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    'source': 'baostock',
                    'exportTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'totalResults': len(export_data),
                    'results': export_data,
                }, f, ensure_ascii=False, default=str)

            self._set_status(f'导出成功: {path}')
            messagebox.showinfo('导出成功', f'已导出 {len(export_data)} 条结果到:\n{path}')
        except Exception as e:
            messagebox.showerror('导出失败', str(e))

    def _open_html(self):
        """打开 index.html"""
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
        if os.path.exists(html_path):
            webbrowser.open(f'file:///{html_path.replace(chr(92), "/")}')
        else:
            messagebox.showinfo('提示', '未找到 index.html 文件')

    # ===================== 辅助方法 =====================

    def _on_filter_change(self):
        """过滤器变化时更新状态"""
        if not self.scanning:
            self._set_status('过滤器已更改，点击"开始扫描"重新扫描')

    def _set_status(self, text):
        self.status_text.config(text=text)

    def _update_time(self):
        self.time_label.config(text=datetime.now().strftime('%Y-%m-%d %H:%M'))

    def _on_close(self):
        if self.scanning:
            if messagebox.askyesno('确认', '扫描正在进行中，确定要退出吗？'):
                self.scanning = False
                self.root.destroy()
        else:
            self.root.destroy()


# ===================== 入口 =====================

def main():
    root = tk.Tk()
    app = StockPickerApp(root)

    # 定期更新时间
    def update_clock():
        app._update_time()
        root.after(30000, update_clock)

    root.after(30000, update_clock)
    root.mainloop()


if __name__ == '__main__':
    main()
