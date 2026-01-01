import csv
import os
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
import argparse

def generate_probability_csv(filename, p_one):
    """
    生成包含0和1概率的CSV文件，其中0的概率为1减去1的概率。
    """
    p_zero = 1 - p_one
    header = ["Byte", "Probability"]
    rows = [[0, p_zero], [1, p_one]]
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        writer.writerows(rows)

def read_input(filename):
    # 读入概率
    byte_prob = {}
    with open(filename, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # 跳过标题行
        for row in reader:
            byte = int(row[0])
            probability = float(row[1])
            byte_prob[byte] = probability
    return byte_prob

# def read_input(filename):
#     # 读入概率
#     byte_prob = {}
#     with open(filename, 'r') as csvfile:
#         reader = csv.reader(csvfile)
#         for row in reader:
#             byte = int(row[0])
#             probability = float(row[1])
#             byte_prob[byte] = probability
#     return byte_prob

def read_dat(filename):
    # 从DAT文件中读取二进制数据
    return np.fromfile(filename, dtype=np.uint8)

def write_dat(data, filename):
    # 将二进制数据写入DAT文件
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    data.tofile(filename)

def compute_cdf(p):
    # 计算给定概率分布的累计概率分布
    return np.array(p).cumsum()

def get_data(cdf, msg_len):
    # 生成给定概率分布长度相同的随机数
    symbol_random = np.random.uniform(size=msg_len)
    # 计算累积概率分布对应的字节符号
    msg = np.searchsorted(cdf, symbol_random, side='right').astype(np.uint8)
    return msg

# def get_data(cdf, msg_len):
#     # 生成给定概率分布长度相同的随机数
#     symbol_random = np.random.uniform(size=msg_len)
#     # 计算累积概率分布对应的字节符号
#     msg = np.searchsorted(cdf, symbol_random)
#     return msg

def simulate_bsc(input_data, noise_data):
    # 模拟二元对称信道（BSC）
    return np.bitwise_xor(input_data, noise_data)

def bsc_workflow(input_file_name, noise_file_name, out_file_name, noise_output_file_name, p_one, msg_len):
    """
    二元对称信道（BSC）工作流。
    """
    # 生成噪声文件
    generate_probability_csv(noise_file_name, p_one)
    # 读取噪声概率分布
    noise_prob = read_input(noise_file_name)
    noise_cdf = compute_cdf(list(noise_prob.values()))
    # 读取输入数据
    input_data = read_dat(input_file_name)
    # 生成噪声数据
    noise_data = get_data(noise_cdf, len(input_data))
    # 写入噪声数据到文件
    write_dat(noise_data, noise_output_file_name)
    # 模拟BSC
    output_data = simulate_bsc(input_data, noise_data)
    # 写入输出数据
    write_dat(output_data, out_file_name)

def parse_sys_args():
    """
    解析命令行参数。
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('in_file_name', type=str, help='输入文件路径')  # 输入文件路径
    parser.add_argument('out_file_name', type=str, help='输出文件路径')  # 输出文件路径
    parser.add_argument('noise_output_file_name', type=str, help='噪声输出文件路径')  # 噪声输出文件路径
    parser.add_argument('msg_len', type=int, help='输出信息长度')  # 输出信息长度
    return parser.parse_args()

def main():
    # 解析命令行参数
    args = parse_sys_args()
    # 运行BSC工作流
    bsc_workflow(args.in_file_name, 'noise.csv', args.out_file_name, args.noise_output_file_name, 0.01, args.msg_len)
    print("done")

if __name__ == '__main__':
    main()
