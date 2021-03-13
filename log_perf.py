#!/usr/bin/python
# python spade_perf.py --log=../release/logs/spade.log --type=ord --png=no

import argparse, numpy, pandas, subprocess, matplotlib.pyplot as plt

INDEX='timestamp'

def load_csv(f):
    return pandas.read_csv(f, delimiter=',')

def lat_min(arr):
    return numpy.percentile(arr, 0)
def lat_max(arr):
    return numpy.percentile(arr, 100)
def lat_99(arr):
    return int(numpy.percentile(arr, 99))

def mean_count_stats(csv):
    count = csv.groupby(INDEX).agg(['mean','count'])
    count.index.name = INDEX
    count.reset_index(inplace=True)
    count.columns = ["_".join(x) for x in count.columns.ravel()]
    count.rename(columns={ count.columns[0]: INDEX }, inplace = True)
    # df2 = df.rename(columns={'a': 'X', 'b': 'Y'})
    return count

def throughput_latency_stats(csv):
    tp_grp = csv.groupby(INDEX).agg({'batches':numpy.sum})
    lat_min_grp = csv.groupby(INDEX).agg({'delay':lat_min, 'proc':lat_min})
    lat_min_new = lat_min_grp.rename(columns={'delay': 'delay_min', 'proc': 'proc_min'})  # inplace=True
    lat_99_grp = csv.groupby(INDEX).agg({'delay':lat_99, 'proc':lat_99})
    lat_99_new = lat_99_grp.rename(columns={'delay':'delay_99', 'proc':'proc_99'})
    lat_max_grp = csv.groupby(INDEX).agg({'delay':lat_max, 'proc':lat_max})
    lat_max_new = lat_max_grp.rename(columns={'delay':'delay_max', 'proc':'proc_max'})

    lat_tmp_1 = pandas.merge(tp_grp,lat_min_new, on=INDEX)
    lat_tmp_new = pandas.merge(lat_tmp_1,lat_99_new, on=INDEX)
    lat_all = pandas.merge(lat_tmp_new,lat_max_new, on=INDEX)
    lat_all.index.name = INDEX
    lat_all.reset_index(inplace=True)
    #column_names = list(lat_all.columns)
    column_names=[INDEX,'batches','delay_min','delay_99','delay_max','proc_min','proc_99','proc_max']
    #column_names.sort()
    #print(column_names)
    lat_all = lat_all.reindex(columns=column_names)
    return lat_all

def show_img(df,data_type,chart_type):
    fig, ax = plt.subplots(figsize=(20, 10))
    ax.set_xlabel('time (s)')
    title = data_type+" "+chart_type+" (batches/sec)"
    mean_position = int(len(df[INDEX])/-25)
    y_mean = 0
    if chart_type == 'throughput':
        ax1 = df.plot(ax=ax, kind='line', x=INDEX, y='batches', label='batches', c='tab:blue')
        # print(list(df[INDEX]))
        y_min = df['batches'].min()
        y_mean = df['batches'].mean()
        y_mean_arr = [y_mean]*len(df[INDEX])
        mean_line = ax.plot(list(df[INDEX]),y_mean_arr, label='Mean', linestyle='--', c='tab:green')
        plt.text(mean_position,y_mean,"%.1f"%y_mean)
        if args.detail == 'yes':
            plt.ylim([y_min,y_mean*3])
        plt.legend(loc='best')
    elif chart_type == 'latency':
        title = data_type+" "+chart_type+" (ms)"
        #ax2 = df.plot(ax=ax, kind='line', x=INDEX, y='delay_min', label='delay_min', c='tab:green')
        #ax3 = df.plot(ax=ax, kind='line', x=INDEX, y='delay_99', label='delay_99', c='tab:gray')
        #ax4 = df.plot(ax=ax, kind='line', x=INDEX, y='delay_max', label='delay_max',c='tab:red')
        ax5 = df.plot(ax=ax, kind='line', x=INDEX, y='proc_min', label='proc_min', c='limegreen')
        ax6 = df.plot(ax=ax, kind='line', x=INDEX, y='proc_99', label='proc_99', c='tab:brown')
        ax7 = df.plot(ax=ax, kind='line', x=INDEX, y='proc_max', label='proc_max', c='red')
        y_mean = df['proc_99'].mean()
        y_mean_arr = [y_mean]*len(df[INDEX])
        mean_line = ax.plot(list(df[INDEX]),y_mean_arr, label='Mean%99', linestyle='--', c='tab:green')
        plt.text(mean_position,y_mean,"%.1f"%y_mean)
        if args.detail == 'yes':
            plt.ylim([0,y_mean*3])
        plt.legend(loc='best')
    elif chart_type == 'batching_stats':
        title = data_type+" "+chart_type+" (mean/count)"
        color1 = 'tab:red'
        color2 = 'tab:green'
        count_line = df.plot(ax=ax, kind='line', x=INDEX, y='batches_count', label='commit_times', c=color1)
        y1_mean = df['batches_count'].mean()
        y1_mean_arr = [y1_mean]*len(df[INDEX])
        count_mean = ax.plot(list(df[INDEX]),y1_mean_arr, label='Mean|commit_times', linestyle='--', c=color1)
        ax.tick_params(axis='y', labelcolor=color1)
        ax.set_ylabel('Commit frequency', color=color1)
        ax.text(mean_position,y1_mean,"%.1f"%y1_mean,c=color1)
        ax.legend(loc='upper left', framealpha=0.5)
        ax2 = ax.twinx()
        ax2.tick_params(axis='y', labelcolor=color2)
        y2_mean = df['batches_mean'].mean()
        y2_mean_arr = [y2_mean]*len(df[INDEX])
        mean_line = df.plot(ax=ax2, kind='line', x=INDEX, y='batches_mean', label='batches/commit', c=color2)
        mean_mean = ax2.plot(list(df[INDEX]),y2_mean_arr, label='Mean|batches/commit', linestyle='--', c=color2)
        ax2.text(len(df[INDEX])-int(mean_position/3),y2_mean,"%.1f"%y2_mean,c=color2)
        ax2.set_ylabel('Batches / Commit', color=color2)
        # fig.tight_layout()
        ax2.legend(loc='upper right', framealpha=0.5)
    plt.title(title)
    plt.grid()
    plt.axis('on')
    plt.xticks(numpy.arange(df.shape[0]))
    if args.png == 'yes':
        plt.savefig(data_type+'_'+type_name+'.png')
    else:
        plt.show()

def exec_cmd(cmd):
    # print(cmd)
    # subprocess.check_output(cmd)
    # with open(csv_file, 'a') as f:
    #     subprocess.call(cmd, shell=True, stdout=f)
    subprocess.call(cmd, shell=True)

def csv_header(csv):
    cmd = ["echo 'timestamp,batches,delay,proc' > "+csv]
    exec_cmd(cmd)
    # with open(csv, 'w') as f:
    #     f.write('timestamp,batches,delay,proc\n')

def csv_trim(csv_file):
    cmd = ["sed -i 's/ms//g' "+csv_file]
    exec_cmd(cmd)

def gen_csv(log_file,log_type):
    csv_file_name = log_type+".csv"
    csv_header(csv_file_name)
    cmd = ["/bin/grep "+log_type+" "+log_file+" | /bin/grep delay| /bin/grep -v ERROR | /bin/awk -v OFS=',' '{print substr($2,1,8),$(NF-3), substr($(NF-1),7), substr($NF,6)}' >> "+csv_file_name]
    exec_cmd(cmd)
    csv_trim(csv_file_name)
    return csv_file_name

def skip_head_tail(csv):
    return csv[1:]

def proc_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log", help="spade log file", type=str, required=True)
    parser.add_argument("-t", "--type", help="perf data type", type=str, default='ord')
    parser.add_argument("-i", "--png", help="save as png",   type=str, default='yes')
    parser.add_argument("-s", "--skip", help="skip head/tail",   type=str, default='yes')
    parser.add_argument("-d", "--detail", help="zoom into details",   type=str, default='yes')
    return parser.parse_args()

args = proc_args()
filename = gen_csv(args.log,args.type)
csv = load_csv(filename)
# csv = skip_head_tail(csv)
lat = throughput_latency_stats(csv)
lat.to_csv("sum_"+filename)          # save csv
show_img(lat,args.type,'throughput')
show_img(lat,args.type,'latency')

count = mean_count_stats(csv)
count.to_csv("count_"+filename)
show_img(count,args.type,'batching_stats')