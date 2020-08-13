
import argparse, json, os, pandas, sqlite3, numpy as np
import matplotlib.pyplot as plt

PCT_THRESHOLD = 7


def read_kv_json(path: str):
    with open(path, 'r') as f:
        jo: dict = json.load(f)
    return jo


def read_config(path):
    return read_kv_json(path)


def arg_file_exist(fname: str):
    if not os.path.exists(fname):
        raise argparse.ArgumentTypeError("File '%s' is not exist" % fname)
    return fname


def select_all(con, sql):
    print("Export Data: "+sql)
    cur = con.cursor()
    cur.execute(sql)
    result = cur.fetchall()
    # print(type(result[0]))  # list( tuple )
    print(result)


def get_count(con, table):
    cur = con.cursor()
    cur.execute("select count(1) from "+table)
    return cur.fetchone()[0]


def get_max(con, table, col, factor=1):
    cur = con.cursor()
    cur.execute("select "+str(factor)+"*max("+col+") from "+table)
    return cur.fetchone()[0]


def get_min(con, table, col, factor=1):
    cur = con.cursor()
    cur.execute("select "+str(factor)+"*min("+col+") from "+table)
    return cur.fetchone()[0]


def exec_sql(con, sql):
    cur = con.cursor()
    cur.execute(sql)


def trim_column(name):
    if '=' in name:
        idx = name.index('=')
        return name[:idx]
    else:
        return name.replace(' ', '_')


def import_csv(con, table, file, header=0, skip=0):
    if not con:
        con = sqlite3.connect(":memory:")  # change to 'sqlite:///your_filename.db'
    if skip > 0 or header > 0:
        # print("header:"+str(header)+" skiprows=range("+str(header+skip)+","+str(header+skip+1)+")")
        df = pandas.read_csv(file, header=header, skiprows=range(header+skip, header+skip+1))
    else:
        df = pandas.read_csv(file)
    df.rename(columns=trim_column, inplace=True)
    # print(df.columns)
    df.to_sql(table, con, if_exists='replace', index=False)
    return con


def calculate(con, sqls):
    for sql in sqls:
        exec_sql(con, sql)


def show_result(con, sqls):
    for sql in sqls:
        select_all(con, sql)


def show_histogram(con, table, col, factor):
    cur = con.cursor()
    sql = "select "+str(factor)+"*"+col+" from "+table
    cur.execute(sql)
    result = cur.fetchall()
    x = np.array(result)
    x_min = get_min(con, table, col, factor)
    x_max = get_max(con, table, col, factor)
    print("\nshow histogram for data: "+table+" | column: "+col+"(*"+str(factor)+") = ("+str(x_min)+","+str(x_max)+")")
    frequency, bins = np.histogram(x, bins=10, range=[x_min, x_max])
    for b, f in zip(bins[1:], frequency):
        print(round(b, 1), ' '.join(np.repeat('*', f)))


def show_histograms(con, sqls):
    for d in sqls:
        show_histogram(con, d.get("table"), d.get("column"), d.get("factor"))


def update_anno(ind, line, anno, ys):
    x, y = line.get_data()
    x0 = x[ind["ind"][0]]
    y0 = y[ind["ind"][0]]
    anno.xy = (x0, y0)
    # print("x="+str(x0) + "y="+str(y0))
    # Get x and y values, then format them to be displayed
    # x_values = " ".join(list(map(str, ind["ind"])))
    # y_values = " ".join(str(ydata[n]) for n in ind["ind"])
    # text = "{}, {}".format(x_values, y_values)
    text = "({}) {:.3f}".format(x0, y0)
    color = "k"
    if len(ys) > 1:
        y1 = ys[0][ind["ind"][0]][0]
        if y0 != y1:
            pct = float(abs(y0 / y1 - 1) * 100)
            if pct > PCT_THRESHOLD:
                color = 'r'
            else:
                color = 'g'
            text = "({}) {:.3f}-{:.3f} \u0394={:.2f}%".format(x0, y0, y1, pct)  # lower case delta \u03B4
    anno.set_text(text)
    anno.set_color(color)
    anno.get_bbox_patch().set_alpha(0.4)


def hover(fig, ax, event, line_info, ys, cross_line):
    cross_line.set_xdata(event.xdata)  # ymin ymax

    line, anno, y = line_info
    vis = anno.get_visible()
    if event.inaxes == ax:
        # Draw annotations if cursor in right position
        cont, ind = line.contains(event)
        if cont:
            update_anno(ind, line, anno, ys)
            anno.set_visible(True)
            fig.canvas.draw_idle()
        else:
            # Don't draw annotations
            if vis:
                anno.set_visible(False)
                fig.canvas.draw_idle()


def plot_line(fig, ax, x, y, ys, cross_line):
    line, = plt.plot(x, y)  # marker="o"
    # Annotation style may be changed here
    anno = ax.annotate("", xy=(0, 0), xytext=(-20, 20), textcoords="offset points", bbox=dict(boxstyle="round", fc="w"),
                       arrowprops=dict(arrowstyle="->"))
    anno.set_visible(False)
    line_info = [line, anno, y]
    # fig.canvas.mpl_connect("motion_notify_event", lambda event: hover(fig, ax, event, line_info))
    fig.canvas.mpl_connect("motion_notify_event", lambda event: hover(fig, ax, event, line_info, ys, cross_line))
    return line


def get_column_data(con, table, col, limit=0):
    cur = con.cursor()
    sql = "select "+col+" from "+table + " limit "+str(limit)
    cur.execute(sql)
    result = cur.fetchall()
    x = np.array(result)
    count = get_count(con, table)
    if count > limit:
        count = limit
    # print("show line chart for data: "+table+" | column: "+col+" limit "+str(limit)+" size "+str(x.shape))
    return count, x


def show_line_charts(con, product, charts):
    for c in charts:  # table.col
        fig, ax = plt.subplots()
        line_chart = c.get("data")
        plotted_lines = []
        legend_names = []
        all_values = []
        limit = c.get("Xlimit")+1
        cross_line = ax.axvline(0, color="k", linewidth=0.6,linestyle='--')
        for columns in line_chart:
            ts = columns.split('.')
            count, values = get_column_data(con, ts[0], ts[1], limit)
            all_values.append(values)
            line = plot_line(fig, ax, range(count), values, all_values, cross_line)
            plotted_lines.append(line)
            legend_names.append(ts[1])
        title = c.get("name")
        yaxis = c.get("Yaxis")
        ax.set(xlabel='Time (Second)', ylabel=yaxis, title=product+'\nMeasured vs AGMlog ( '+title+" )")
        # plt.legend(plotted_lines, legend_names, loc='upper left', bbox_to_anchor=(0, 1.07), prop={'size': 7})
        plt.legend(plotted_lines, legend_names, loc='best', prop={'size': 6})
        # ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.05), ncol=3, fancybox=True, shadow=True)
        ax.grid()

        plot_margin = 0.1
        x0, x1, y0, y1 = plt.axis()
        plt.axis((x0 - plot_margin, x1 + plot_margin, y0 - plot_margin, y1 + plot_margin))
        # fig.savefig("test.png")
    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process Data in CSV')
    parser.add_argument('--config', type=arg_file_exist, default="", help='Config File')
    args = parser.parse_args()
    CONFIG = read_kv_json(args.config)
    # print(CONFIG.get("map"))
    file1: str = CONFIG.get("data").get("file").get("CSV1")
    file2: str = CONFIG.get("data").get("file").get("CSV2")
    headers: list = CONFIG.get("data").get("header")
    conn = import_csv(None, "CSV1", file1, headers[0].get("name"), headers[0].get("skip"))
    conn = import_csv(conn, "CSV2", file2, headers[1].get("name"), headers[1].get("skip"))

    calculate(conn, CONFIG.get("calculate"))
    show_result(conn, CONFIG.get("result"))

    # show_histograms(conn, CONFIG.get("histogram"))
    PCT_THRESHOLD = CONFIG.get("data").get("threshold")
    show_line_charts(conn, CONFIG.get("product"), CONFIG.get("chart"))

    conn.commit()
    conn.close()
