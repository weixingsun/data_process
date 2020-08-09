import argparse, json, os, pandas, sqlite3, numpy


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
        print("header:"+str(header)+" skiprows=range("+str(header+skip)+","+str(header+skip+1)+")")
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
    print("\nshow dist for table: "+table+" column: "+col+" ("+str(x_min)+","+str(x_max)+") with factor: "+str(factor))
    frequency, bins = numpy.histogram(x, bins=10, range=[x_min, x_max])
    for b, f in zip(bins[1:], frequency):
        print(round(b, 1), ' '.join(numpy.repeat('*', f)))


def show_distos(con, sqls):
    for d in sqls:
        show_disto(con, d.get("table"), d.get("column"), d.get("factor"))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process Data in CSV')
    parser.add_argument('--config', type=arg_file_exist, default="", help='Config File')
    args = parser.parse_args()
    CONFIG = read_kv_json(args.config)
    # print(CONFIG.get("map"))
    h = CONFIG.get("header")
    conn = import_csv(None, "CSV1", CONFIG.get("CSV1"), h[0].get("name"), h[0].get("skip"))
    conn = import_csv(conn, "CSV2", CONFIG.get("CSV2"), h[1].get("name"), h[1].get("skip"))

    calculate(conn, CONFIG.get("calculate"))
    show_result(conn, CONFIG.get("result"))

    # select_all(conn, "select AVG_ROC_P from group2")
    show_distos(conn, CONFIG.get("histogram"))

    conn.commit()
    conn.close()
