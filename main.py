import argparse, json, os, pandas, sqlite3, numpy
import matplotlib.pyplot as plt

def read_kv_json(path):
    with open(path, 'r') as f:
        jo: dict = json.load(f)
    return jo


def read_config(path):
    return read_kv_json(path)


def arg_file_exist(fname):
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


def show_disto(con, table, col, factor):
    cur = con.cursor()
    sql = "select "+str(factor)+"*"+col+" from "+table
    cur.execute(sql)
    result = cur.fetchall()
    x = numpy.array(result)
    x_min = get_min(con,table,col,factor)
    x_max = get_max(con,table,col,factor)
    print("\nshow histogram for data: "+table+" | column: "+col+"(*"+str(factor)+") = ("+str(x_min)+","+str(x_max)+")")
    frequency, bins = numpy.histogram(x, bins=10, range=[x_min, x_max])
    for b, f in zip(bins[1:], frequency):
        print(round(b, 1), ' '.join(numpy.repeat('*', f)))


def show_distos(con, sqls):
    for d in sqls:
        show_disto(con, d.get("table"), d.get("column"), d.get("factor"))


def update_annot(ind, line, annot, ydata):
    x, y = line.get_data()
    annot.xy = (x[ind["ind"][0]], y[ind["ind"][0]])
    # Get x and y values, then format them to be displayed
    x_values = " ".join(list(map(str, ind["ind"])))
    y_values = " ".join(str(ydata[n]) for n in ind["ind"])
    text = "{}, {}".format(x_values, y_values)
    annot.set_text(text)
    annot.get_bbox_patch().set_alpha(0.4)


def hover(fig, ax, event, line_info):
    line, annot, ydata = line_info
    vis = annot.get_visible()
    if event.inaxes == ax:
        # Draw annotations if cursor in right position
        cont, ind = line.contains(event)
        if cont:
            update_annot(ind, line, annot, ydata)
            annot.set_visible(True)
            fig.canvas.draw_idle()
        else:
            # Don't draw annotations
            if vis:
                annot.set_visible(False)
                fig.canvas.draw_idle()


def plot_line(fig, ax, x, y):
    line, = plt.plot(x, y)  # marker="o"
    # Annotation style may be changed here
    annot = ax.annotate("", xy=(0, 0), xytext=(-20, 20), textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="w"),
                        arrowprops=dict(arrowstyle="->"))
    annot.set_visible(False)
    line_info = [line, annot, y]
    fig.canvas.mpl_connect("motion_notify_event", lambda event: hover(fig, ax, event, line_info))


def get_line_data(con, table, col):
    # plt.logplt.plot(x, y)
    cur = con.cursor()
    sql = "select "+col+" from "+table
    cur.execute(sql)
    result = cur.fetchall()
    x = numpy.array(result)
    count = get_count(con,table)
    # print("\nshow line chart for data: "+table+" | column: "+col)
    return count,x


def show_line_charts(con, charts):
    for c in charts:  # table.col
        fig, ax = plt.subplots()
        ls = c.get("data")
        for l in ls:
            ts = l.split('.')
            count,x = get_line_data(con, ts[0], ts[1])
            plot_line(fig, ax, range(count), x)
        title = c.get("name")
        ax.set(xlabel='time (Second)', ylabel='Power (Watt)', title='Measured vs AGMlog '+title)
        ax.grid()
        # fig.savefig("test.png")
        plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process Data in CSV')
    parser.add_argument('--config', type=arg_file_exist, default="", help='Config File')
    args = parser.parse_args()
    CONFIG = read_kv_json(args.config)
    # print(CONFIG.get("map"))
    h = CONFIG.get("header")
    conn = import_csv(None, "CSV1", CONFIG.get("data").get("CSV1"), h[0].get("name"), h[0].get("skip"))
    conn = import_csv(conn, "CSV2", CONFIG.get("data").get("CSV2"), h[1].get("name"), h[1].get("skip"))

    calculate(conn, CONFIG.get("calculate"))
    show_result(conn, CONFIG.get("result"))

    # select_all(conn, "select AVG_ROC_P from group2")
    # show_distos(conn, CONFIG.get("histogram"))
    show_line_charts(conn, CONFIG.get("chart"))

    conn.commit()
    conn.close()
