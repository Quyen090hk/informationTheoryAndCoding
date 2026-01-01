import numpy as np
import argparse  # 导入argparse模块，用于处理命令行参数
import timeit
# 全局变量定义
verbose_output = False  # 是否输出详细信息的标志
save_distribution = False  # 是否保存字节分布的标志
distribution_file = ""  # 存储字节分布的文件路径


def probability(x):
    #将数组x的元素分到256个区间的直方图中，hist对应每个区间的元素个数
    (hist, bin_edges) = np.histogram(x, bins=range(257))
    P = hist/x.size
    return P

def self_info(P):
    P = np.where(P==0, np.spacing(1), P)
    return -np.log2(P)

def entropy(P):
    return np.sum(P*self_info(P))

class CustomParser(argparse.ArgumentParser):
    """自定义命令行参数解析器，继承自argparse.ArgumentParser"""
    def error(self, message):
        """
        重写error方法，自定义错误处理
        :param message: 错误信息
        """
        self.print_help()  # 打印帮助信息
        exit(1)  # 以错误状态码1退出程序

def setup_cli():
    """设置命令行界面，定义和解析命令行参数"""
    global input_file, output_file  # 声明全局变量，用于存储源文件和结果文件的路径
    # 创建自定义的命令行解析器实例
    cli = CustomParser(description="Analyze byte-level information content of a file.")
    # 添加命令行参数
    #-----------------------------------------做了修改---------------------------------
    # -d 或 --dist：可选参数，用于指定保存字节分布的文件
    cli.add_argument("-p", "--export", type=str, metavar='DIST_FILE', help="save byte distribution to file")
    # -v 或 --verbose：可选标志，用于启用详细输出
    cli.add_argument("-v", "--verbose", action="store_true", help="enable detailed output")
    # INPUT：必需参数，指定要分析的源文件
    cli.add_argument("INPUT", type=str, help="source file for analysis")
    # OUTPUT：必需参数，指定存储分析结果的文件
    cli.add_argument("OUTPUT", type=str, help="file to store analysis results")
    # 解析命令行参数
    args = cli.parse_args()
    # 将解析后的源文件和结果文件路径赋值给全局变量
    input_file = args.INPUT
    output_file = args.OUTPUT
    # 处理详细输出选项
    if args.verbose:
        global verbose_output
        verbose_output = True  # 如果指定了-v参数，设置详细输出标志为True
    # 处理保存分布选项
    if args.export:
        global save_distribution, distribution_file
        save_distribution = True  # 如果指定了-d参数，设置保存分布标志为True
        distribution_file = args.export  # 保存指定的分布文件路径

#计算输入文件的信息量
#输入的x是一个numpy数组对象（此行可删）
def compute_info(x):
    P = probability(x)
    info = entropy(P)	#计算输入文件的信息熵，即要求的信息量

    # 获取当前文件每个符号的概率分布，然后存入指定的文件distribution_file中
    if save_distribution:
        try:
            with open(distribution_file,"w") as f:
                # f.write("{}'s distribution:\n".format(input_file))
                for i in range(256):
                    f.write("{},{}\n".format(i,P[i]))
        except Exception as e:
            print("发生错误",e)

    return info

def IO(input_file,output_file):
    """
    参数:1.输入文件input_file（路径，str类型）
        2.输出文件output_file（路径，str类型）
    功能：处理input_file，得到它的字节长度以及信息熵，将它的文件名称（路径），字节长度
        以及信息熵写入到输出文件中
    返回值：无
    """
    try:
        # 将文件转成ndarray类型
        file_ndarray = np.fromfile(input_file, dtype=np.uint8)

        # 计算指定文件的信息熵。
        I = compute_info(file_ndarray)

        # 以二进制的方法读取该文件
        with open(input_file,"rb") as f1:
            data = f1.read() # 获取该文件的所有数据（数据都是字节形式）
            length = len(data) # 获取文件字节数

            # 数据包含1.文件的名称，2.文件的信息熵（保留六位小数），3.文件的长度，用逗号分开
            msg = ["\"{}\",".format(input_file),"\"{:.6f}\",".format(I),"\"{}\"".format(length)]

            # 将数据添加到输出文件中
            with open(output_file,mode = 'a',newline = '',encoding= 'utf-8') as f2:
                for m in msg:
                    f2.write(m) # 依次写入数据
                f2.write("\r\n") # 换行

        # 获取具体的文件细节
        if verbose_output:
            time = timeit.timeit(lambda:compute_info(file_ndarray),number = 10)/10 #运行10次取平均值

            # 打印文件执行时间，每个符号（字节）的信息量，字节长度。
            print("[", time," sec]", input_file, ":", "{:.6f}".format(I), "bit/sym,", length, "bytes")
    except Exception as e:
        print("发生错误",e)

def main():
    setup_cli()
    IO(input_file,output_file)

if __name__ == "__main__":
    main()