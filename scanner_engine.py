#!/usr/bin/env python3
"""强势调整选股引擎 — baostock 数据源"""
import json, time, os, sys, socket
from datetime import datetime, timedelta

# 防止 baostock 服务器不可达时无限挂死
socket.setdefaulttimeout(10)

try:
    import baostock as bs
except ImportError:
    print("请安装 baostock: pip install baostock")
    sys.exit(1)

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scan_result.json')

# ===================== 股票列表 =====================

def get_stock_list(exclude_st=True, market_filter='all', already_logged_in=False):
    """获取A股列表
    market_filter: 'all' | 'sh' | 'sz' | '主板' | '创业板' | '科创板'
    already_logged_in: True 表示调用方已登录 baostock，本函数不再重复登录/登出
    """
    if not already_logged_in:
        lg = bs.login()
        if lg.error_code != '0':
            raise Exception(f"baostock 登录失败: {lg.error_msg}")

    rs = bs.query_stock_basic()
    if rs.error_code != '0':
        if not already_logged_in:
            bs.logout()
        raise Exception(f"获取股票列表失败: {rs.error_msg}")

    stocks = []
    while (rs.error_code == '0') and rs.next():
        row = rs.get_row_data()
        code_full = row[0]      # e.g. sh.600519
        code_name = row[1]       # e.g. 贵州茅台
        ipo_date = row[2]        # IPO date

        if not code_full or not code_name:
            continue

        # 提取代码
        code = code_full.split('.')[-1] if '.' in code_full else code_full
        if len(code) != 6:
            continue

        # 排除指数 (sh.000xxx, sh.399xxx, sz.399xxx 等)
        if code_full.startswith('sh.000') or code_full.startswith('sh.399') or code_full.startswith('sz.399'):
            continue
        # 排除B股
        if code.startswith('900') or code.startswith('200'):
            continue
        # 排除转债 (sh.1xxxxx, sz.1xxxxx)
        if code.startswith(('10', '11', '12')):
            continue
        # 排除基金/ETF (sh.5xxxxx, sz.5xxxxx, sz.1xxxxx)
        if code.startswith('5'):
            continue

        # 只保留沪深A股代码范围
        is_sh = code.startswith(('60', '68'))
        is_sz = (code.startswith('00') or code.startswith('30'))
        if not is_sh and not is_sz:
            continue

        market = 'SH' if code_full.startswith('sh.') else 'SZ'

        # 排除ST
        if exclude_st and ('ST' in code_name or '*ST' in code_name or 'st' in code_name.lower()):
            continue

        # 排除退市
        if '退' in code_name:
            continue

        # 排除新股 (上市不足120天)
        if ipo_date:
            try:
                ipo_dt = datetime.strptime(ipo_date, '%Y-%m-%d')
                if (datetime.now() - ipo_dt).days < 120:
                    continue
            except:
                pass

        # 判断板块
        if code.startswith('688'):
            board = '科创板'
        elif code.startswith('30'):
            board = '创业板'
        else:
            board = '主板'

        # 市场过滤
        if market_filter == 'sh' and market != 'SH':
            continue
        if market_filter == 'sz' and market != 'SZ':
            continue
        if market_filter == '主板' and board != '主板':
            continue
        if market_filter == '创业板' and board != '创业板':
            continue
        if market_filter == '科创板' and board != '科创板':
            continue

        stocks.append({
            'code': code,
            'name': code_name,
            'market': market,
            'board': board,
            'baostock_code': code_full,
            'ipo_date': ipo_date,
        })

    if not already_logged_in:
        bs.logout()
    return stocks


# ===================== 选股逻辑 =====================

def screen(stock, kline):
    """
    强势调整选股策略:
    1. 最近8天内出现涨停（涨幅>=9.85%且上影线极小）
    2. 涨停后股价始终在涨停最低价之上（未跌破）
    3. 评分: 涨停+2, 试盘线+2, 大阳线+1
    4. 生成买入信号和止损位
    """
    if len(kline) < 60:
        return None

    # 计算移动平均线
    for i in range(len(kline)):
        kline[i]['ma5'] = sum(kline[j]['close'] for j in range(max(0, i - 4), i + 1)) / min(5, i + 1)
        kline[i]['ma20'] = sum(kline[j]['close'] for j in range(max(0, i - 19), i + 1)) / min(20, i + 1) if i >= 19 else None

    last = kline[-1]

    # 股价必须在MA20之上
    if not last['ma20'] or last['close'] <= last['ma20']:
        return None

    # 涨停阈值:主板 10% / 创业板·科创板 20%(2026-07-06新规后 ST 已随板块统一,不再单独5%)
    if stock.get('board') in ('创业板', '科创板'):
        th = 19.8
    else:
        th = 9.85
    trigger = None

    # 在最近8天内找涨停触发日
    for i in range(len(kline) - 1, max(0, len(kline) - 9), -1):
        d = kline[i]
        pc = (kline[i - 1]['close'] if i > 0 else d.get('preClose')) or d['open']
        if not pc or pc == 0:
            continue
        pct = (d['close'] - pc) / pc * 100

        # 涨停条件: 涨幅>=9.85% 且上影线很小(hight-close <= 0.02元)
        if pct >= th and (d['high'] - d['close']) <= 0.02:
            # 排除连续涨停（前一日也是涨停）
            if i > 0:
                pp = kline[i - 1]
                ppc = (kline[i - 2]['close'] if i > 1 else pp.get('preClose')) or pp['open']
                if ppc and ppc > 0 and (pp['close'] - ppc) / ppc * 100 >= th:
                    continue
            # 排除当日即开板（次日涨幅也超9.85%）
            if i < len(kline) - 1:
                nd = kline[i + 1]
                if (nd['close'] - d['close']) / d['close'] * 100 >= th:
                    continue
            trigger = i
            break

    if trigger is None:
        return None

    # 止损位: 涨停日最低价
    trigger_low = kline[trigger]['low']

    # 涨停后不能跌破止损位
    for i in range(trigger, len(kline)):
        if kline[i]['low'] < trigger_low:
            return None

    # ===== 评分系统 =====
    score, details = 0, []

    for i in range(max(0, len(kline) - 40), len(kline)):
        d = kline[i]
        pc = (kline[i - 1]['close'] if i > 0 else d.get('preClose')) or d['open']
        if not pc or pc == 0:
            continue
        pct = (d['close'] - pc) / pc * 100

        if pct >= th and (d['high'] - d['close']) <= 0.02:
            # 涨停
            score += 2
            details.append({
                'date': d['date'], 'type': '涨停', 'score': 2,
                'reason': f'涨幅{pct:.1f}%'
            })
        elif d['close'] > d['open']:
            entity = d['close'] - d['open']
            entity_pct = entity / d['open'] * 100
            upper_shadow = d['high'] - max(d['open'], d['close'])

            if entity_pct < 3 and entity > 0 and upper_shadow >= 2 * entity:
                # 试盘线：小实体 + 长上影线
                score += 2
                details.append({
                    'date': d['date'], 'type': '试盘线', 'score': 2,
                    'reason': f'上影/实体={upper_shadow / entity:.1f}'
                })
            elif entity_pct > 3:
                # 大阳线
                score += 1
                details.append({
                    'date': d['date'], 'type': '大阳线', 'score': 1,
                    'reason': f'实体{entity_pct:.1f}%'
                })

    # ===== 买入信号 =====
    buy_date, buy_price = None, None
    for i in range(trigger + 3, len(kline)):
        d = kline[i]
        pc = (kline[i - 1]['close'] if i > 0 else d.get('preClose')) or d['open']
        if (pc and d['close'] > d['open']
                and (d['close'] - pc) / pc * 100 > 0
                and d.get('ma5') and d['close'] > d['ma5']):
            buy_date, buy_price = d['date'], d['close']
            break

    # ===== 风险计算 =====
    stop_loss = trigger_low
    bp = buy_price or last['close']
    risk = (bp - stop_loss) / bp if bp else 1
    if risk > 0.1:
        stop_loss = bp * 0.9
        risk = 0.1

    return {
        'code': stock['code'],
        'name': stock['name'],
        'market': stock['market'],
        'board': stock.get('board', '主板'),
        'latestPrice': last['close'],
        'pctChange': (last['close'] - kline[-2]['close']) / kline[-2]['close'] * 100
                     if kline[-2].get('close') else 0,
        'totalScore': score,
        'scoreDetails': details,
        'triggerLimitDate': kline[trigger]['date'],
        'triggerLimitIndex': trigger,
        'triggerClose': kline[trigger]['close'],
        'kline': kline,
        'buySignalDate': buy_date,
        'buyPrice': buy_price,
        'stopLoss': round(stop_loss, 2),
        'riskPct': round(risk, 4),
        'hasBuySignal': buy_date is not None,
        'isStopBroken': last['close'] < stop_loss,
        'status': '有效' if buy_date else '暂无买点',
    }


# ===================== 主扫描逻辑 =====================

def run_scan(exclude_st=True, market_filter='all', max_stocks=None, progress_callback=None, stop_event=None, **kwargs):
    """
    执行完整扫描（单次baostock登录，大幅提速）
    progress_callback(phase, current, total, message)
    stop_event: threading.Event 对象，设置时停止扫描
    kwargs: min_turnover, max_turnover, min_amount
    返回: (results_list, total_stocks_scanned)
    """
    start_time = time.time()

    # ===== 单次登录，全程复用 =====
    lg = bs.login()
    if lg.error_code != '0':
        raise Exception(f'baostock 登录失败: {lg.error_msg}')

    # 第一阶段: 获取股票列表（复用已登录会话）
    if progress_callback:
        progress_callback('list', 0, 0, '正在获取A股列表...')

    all_stocks = get_stock_list(exclude_st=exclude_st, market_filter=market_filter, already_logged_in=True)

    if max_stocks:
        all_stocks = all_stocks[:max_stocks]

    total = len(all_stocks)
    if progress_callback:
        progress_callback('list', total, total, f'获取到 {total} 只股票，开始扫描...')

    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=250)).strftime('%Y-%m-%d')

    # 筛选条件
    min_turnover = kwargs.get('min_turnover', 0)      # 最低换手率(%)
    max_turnover = kwargs.get('max_turnover', 100)     # 最高换手率(%)
    min_amount = kwargs.get('min_amount', 0)            # 最低成交额(元)

    results = []
    scan_count = 0
    error_count = 0
    skip_turnover = 0
    skip_amount = 0

    for i, stock in enumerate(all_stocks):
        # 检查停止信号
        if stop_event and stop_event.is_set():
            if progress_callback:
                progress_callback('scan', i, total, f'用户停止 | 已扫描 {i}/{total} | 候选 {len(results)}')
            break

        try:
            # 直接查询K线（复用已登录的会话）
            rs = bs.query_history_k_data_plus(
                stock['baostock_code'],
                'date,open,high,low,close,volume,amount,preclose,turn,tradestatus',
                start_date=start_date,
                end_date=end_date,
                frequency='d',
                adjustflag='2'
            )

            klines = []
            if rs.error_code == '0':
                while (rs.error_code == '0') and rs.next():
                    row = rs.get_row_data()
                    try:
                        klines.append({
                            'date': row[0],
                            'open': float(row[1]),
                            'high': float(row[2]),
                            'low': float(row[3]),
                            'close': float(row[4]),
                            'volume': float(row[5]),
                            'amount': float(row[6]) if row[6] else 0,
                            'preClose': float(row[7]) if row[7] else 0,
                            'turn': float(row[8]) if row[8] and len(row) > 8 else 0,
                        })
                    except (ValueError, IndexError):
                        continue

            # 截取最近120条
            if len(klines) > 120:
                klines = klines[-120:]

            scan_count += 1

            if len(klines) < 30:
                if progress_callback and (i + 1) % 100 == 0:
                    progress_callback('scan', i + 1, total,
                                      f'扫描中 {i+1}/{total} | 候选 {len(results)} | 换手过滤 {skip_turnover} | 跳过数据不足')
                continue

            # === 换手率 & 成交额过滤 ===
            latest = klines[-1]
            avg_turn = sum(k['turn'] for k in klines[-5:] if k['turn'] > 0) / max(1, sum(1 for k in klines[-5:] if k['turn'] > 0))

            if avg_turn > 0:
                if avg_turn < min_turnover or avg_turn > max_turnover:
                    skip_turnover += 1
                    if progress_callback and (i + 1) % 200 == 0:
                        progress_callback('scan', i + 1, total,
                                          f'扫描中 {i+1}/{total} | 候选 {len(results)} | 换手过滤 {skip_turnover} | 成交额过滤 {skip_amount}')
                    continue

            if min_amount > 0 and latest['amount'] < min_amount:
                skip_amount += 1
                if progress_callback and (i + 1) % 200 == 0:
                    progress_callback('scan', i + 1, total,
                                      f'扫描中 {i+1}/{total} | 候选 {len(results)} | 换手过滤 {skip_turnover} | 成交额过滤 {skip_amount}')
                continue

            r = screen(stock, klines)

            if r:
                results.append(r)
                if progress_callback:
                    progress_callback('hit', i + 1, total,
                                      f'★ {stock["code"]} {stock["name"]} 评分{r["totalScore"]} | 候选 {len(results)}')
            elif progress_callback and (i + 1) % 100 == 0:
                progress_callback('scan', i + 1, total,
                                  f'扫描中 {i+1}/{total} | 候选 {len(results)} | 报错 {error_count}')

        except Exception as e:
            error_count += 1
            scan_count += 1
            if progress_callback and error_count <= 5:
                progress_callback('error', i + 1, total, f'{stock["code"]} {str(e)[:60]}')

    # ===== 扫描完成，登出 =====
    bs.logout()

    # 排序: 评分降序, 触发日降序, 有买点优先, 风险升序
    results.sort(key=lambda x: (
        -x['totalScore'],
        x['triggerLimitDate'],
        not x['hasBuySignal'],
        x['riskPct']
    ))

    elapsed = time.time() - start_time

    # 保存结果
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({
            'source': 'baostock',
            'scanTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total': total,
            'scanned': scan_count,
            'matches': len(results),
            'errors': error_count,
            'elapsed': round(elapsed, 1),
            'results': results,
        }, f, ensure_ascii=False, default=str)

    if progress_callback:
        progress_callback('done', total, total,
                          f'扫描完成! {len(results)} 只符合 | 耗时 {elapsed:.1f}秒 | 报错 {error_count} | 换手过滤 {skip_turnover} | 成交额过滤 {skip_amount}')

    return results, total


# ===================== 命令行入口 =====================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='强势调整选股引擎 (baostock)')
    parser.add_argument('--include-st', action='store_true', default=False, help='包含ST股票')
    parser.add_argument('--include-chinext', action='store_true', default=False, help='包含创业板(300xxx)')
    parser.add_argument('--include-star', action='store_true', default=False, help='包含科创板(688xxx)')
    parser.add_argument('--min-turnover', type=float, default=0, help='最低近5日平均换手率(%%)，默认0=不过滤')
    parser.add_argument('--max-turnover', type=float, default=100, help='最高近5日平均换手率(%%)，默认100=不过滤')
    parser.add_argument('--min-amount', type=float, default=0, help='最低成交额(万元)，默认0=不过滤')
    parser.add_argument('--max-stocks', type=int, default=0, help='最多扫描股票数，默认0=全部(~5000只)')
    parser.add_argument('--all', action='store_true', default=False, help='包含全部板块(ST+创业板+科创板)')
    args = parser.parse_args()

    # 确定市场过滤
    if args.all:
        market_filter = 'all'
        exclude_st = False
    elif args.include_st or args.include_chinext or args.include_star:
        # 自定义组合
        exclude_st = not args.include_st
        parts = ['主板']
        if args.include_chinext: parts.append('创业板')
        if args.include_star: parts.append('科创板')
        # 使用 'all' 但单独排除 ST
        market_filter = 'all'
    else:
        market_filter = '主板'
        exclude_st = True

    max_stocks = args.max_stocks if args.max_stocks > 0 else None
    min_amount = args.min_amount * 10000 if args.min_amount > 0 else 0  # 万元转元

    print('=' * 60)
    print(f'  强势调整选股引擎 (baostock)')
    print(f'  时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'  板块: {market_filter} | 排除ST: {exclude_st}')
    print(f'  换手率: {args.min_turnover}%~{args.max_turnover}% | 最低成交额: {args.min_amount}万元')
    print(f'  限制: {"全部" if max_stocks is None else max_stocks} 只')
    print('=' * 60)

    def cli_progress(phase, cur, total, msg):
        if phase in ('list', 'done'):
            print(f'\n{msg}')
        elif phase == 'hit':
            print(f'  {msg}')
        elif phase == 'scan':
            print(f'\r  {msg}', flush=True)

    results, total = run_scan(
        exclude_st=exclude_st,
        market_filter=market_filter,
        max_stocks=max_stocks,
        progress_callback=cli_progress,
        min_turnover=args.min_turnover,
        max_turnover=args.max_turnover,
        min_amount=min_amount,
    )

    print(f'\n\n===== {len(results)} 只符合强势调整 =====')
    for i, r in enumerate(results[:20]):
        print(f'  {i+1}. {r["code"]} {r["name"]:　<6} '
              f'评分{r["totalScore"]:>2} '
              f'涨停日{r["triggerLimitDate"]} '
              f'B:{r["buySignalDate"] or "无":　<12} '
              f'止损{r["stopLoss"]}')

    print(f'\n结果已保存至: {OUTPUT}')


if __name__ == '__main__':
    main()
