import numpy as np
import csv
import argparse # 导入argparse模块，用于处理命令行参数
import struct
import time,os


# 全局变量定义
start_time = 0  # 算法开始时间
end_time = 0  # 算法结束时间
verbose_output = False  # 是否输出详细信息的标志
input_file = ""  # 输入文件路径
output_file = ""  # 输出文件路径
msg_len = 0  # 生成消息的长度


class CustomParser(argparse.ArgumentParser):
    """自定义命令行参数解析器，用于更友好的错误处理"""

    def error(self, message):
        """重写错误处理方法，在出错时打印帮助信息并退出"""
        self.print_help()  # 打印帮助信息
        exit(1)   # 以错误状态码1退出程序

def setup_cli():
    """设置命令行界面，解析命令行参数"""
    global input_file, output_file, msg_len, verbose_output
    # 创建自定义的命令行解析器实例
    cli = CustomParser(description="Simulation of Discrete Memoryless Source")
    # -v 或 --verbose：可选标志，用于启用详细输出
    cli.add_argument("-v", "--verbose", action="store_true", help="display detailed messages")
    # INPUT：必需参数，指定要分析的源文件
    cli.add_argument("INPUT", type=str, help="path to the input file with symbol probability distribution")
    # OUTPUT：必需参数，指定存储分析结果的文件
    cli.add_argument("OUTPUT", type=str, help="path to the output file of a long message")
    # MSG_LEN:输出信息的长度
    cli.add_argument("MSG_LEN", type=int, help="length of the output message (in symbols)")

    # 解析命令行参数
    args = cli.parse_args()
    # 将解析后的源文件和结果文件路径赋值给全局变量
    input_file = args.INPUT
    output_file = args.OUTPUT
    msg_len = args.MSG_LEN
    # 处理详细输出选项
    if args.verbose:
        global verbose_output
        verbose_output = True  # 如果指定了-v参数，设置详细输出标志为True


# 从输入文件中读取符号概率分布
def read_input(in_file_name):
    symbol_prob = np.zeros(256)      # 创建一个大小为256的全零数组，用于存储符号概率分布
    with open(in_file_name, "rt") as csvfile_read:
        csv_reader = csv.reader(csvfile_read)
        row = [r[1] for r in csv_reader]  # 读取第二列数据并保存在row列表中
    for i in range(0, 256):
        symbol_prob[i] = float(row[i])  # 将数据转换为浮点数并保存在符号概率分布数组中

    return symbol_prob


def write_output(output_file_name, msg):
    """将生成的消息写入文件，每行一个数字"""
    msg = np.clip(msg, 0, 255).astype(np.uint8)  # 将值限制在0-255之间，并转换为无符号8位整数

    with open(output_file_name, 'wb') as f:  # 以二进制方式写入，而不是字符串
        for num in msg:
            f.write(struct.pack("B", num))  # 将数据num打包成无符号的字符(B)

def generate_msg(symbol_prob, length):
    """根据符号概率分布生成指定长度的消息"""
    cdf = np.cumsum(symbol_prob)  # 计算累积分布函数
    symbol_random = np.random.uniform(size=length)  # 生成均匀分布的随机数
    msg = np.searchsorted(cdf, symbol_random)  # 使用反函数法生成符合给定分布的随机数
    return msg


def workflow(INPUT, OUTPUT, MSG_LEN):
    """执行整个工作流程：读取输入、生成消息、写入输出"""
    global start_time, end_time
    start_time = time.time()
    symbol_prob = read_input(INPUT)  # 读取符号概率分布
    msg = generate_msg(symbol_prob, MSG_LEN)  # 生成消息
    write_output(OUTPUT, msg)  # 写入输出文件
    end_time = time.time()
    if verbose_output:
        print(f"[{end_time - start_time:.6f} sec]")  # 如果启用详细输出，打印执行时间


# 将2比特的概率分布转换成256比特的概率分布
def DMS_2bit(file_2bit):
    symbol_prob_2bit = np.zeros(2)
    symbol_prob_256 = np.zeros(256)

    # 固定使用同级 data/temp/file_2bit_to_256bit 目录（相对 src 目录的上级）
    temp_dir = os.path.join("..", "data", "temp", "file_2bit_to_256bit")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # 正确提取输入文件名（不带路径、不带扩展名）
    base_name = os.path.basename(file_2bit)                  # e.g. "p=0.01.csv"
    name_without_ext = os.path.splitext(base_name)[0]        # e.g. "p=0.01"
    out_file_name = os.path.join(temp_dir, f"{name_without_ext}.256.csv")

    with open(out_file_name, "w") as f:
        with open(file_2bit) as in_file:
            csv_reader = csv.reader(in_file)
            for x, p in csv_reader:
                symbol_prob_2bit[int(x)] = float(p)

        for i in range(256):
            count = bin(i).count('1')
            symbol_prob_256[i] = (symbol_prob_2bit[0] ** (8 - count)) * (symbol_prob_2bit[1] ** count)
            f.write(f'{i},{symbol_prob_256[i]:.8f}\n')

    return out_file_name


if __name__ == '__main__':
    """主函数，控制整个程序的执行流程"""
    setup_cli()  # 设置命令行界面
    num_lines = sum(1 for _ in open(input_file))  # 计算输入文件的行数
    if num_lines == 2:
        # 如果输入文件只有两行，说明是2比特分布，需要转换为256比特
        input_file_to_256_name = DMS_2bit(input_file)
    else:
        # 否则直接使用原输入文件
        input_file_to_256_name = input_file
    workflow(input_file_to_256_name, output_file, msg_len)  # 执行主要工作流程
