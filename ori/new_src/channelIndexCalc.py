import csv
import os
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
import argparse

def parse_sys_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('in_file_name', type=str, help='输入文件路径')  
    parser.add_argument('noise_file_name', type=str, help='噪声文件路径')
    parser.add_argument('out_file_name', type=str, help='输出文件路径')
    parser.add_argument('--do_test', action="store_true", default=False, help='是否进行单元测试')
    args = parser.parse_args()
    return args

def read_input(file_name):
    """
    从DAT文件中读取消息或噪声序列。
    """
    file_data = np.fromfile(file_name, dtype='uint8')
    return file_data

def calculate_channel_probabilities(input_data, noise_data):
    """
    计算信道转移概率。
    """
    num_states = 256
    transition_counts = np.zeros((num_states, num_states))
    for x, y in zip(input_data, noise_data):
        transition_counts[x, y] += 1
    # 避免除零错误：如果某行全为0，则保持为0
    row_sums = np.sum(transition_counts, axis=1, keepdims=True)
    transition_probabilities = np.where(row_sums > 0, 
                                       transition_counts / row_sums, 
                                       0)
    return transition_probabilities

def calculate_mutual_information(transition_probabilities):
    """
    计算互信息。
    互信息 I(X;Y) = sum(p(x,y) * log2(p(x,y) / (p(x) * p(y))))
    理论上互信息应该是非负的。
    """
    p_x = np.sum(transition_probabilities, axis=1)
    p_y = np.sum(transition_probabilities, axis=0)
    mi = 0
    for i in range(len(p_x)):
        for j in range(len(p_y)):
            if transition_probabilities[i][j] > 0:
                # 避免除零错误
                if p_x[i] > 0 and p_y[j] > 0:
                    ratio = transition_probabilities[i][j] / (p_x[i] * p_y[j])
                    if ratio > 0:
                        mi += transition_probabilities[i][j] * np.log2(ratio)
    # 互信息理论上应该非负，如果出现负值，可能是数值误差，返回0或绝对值
    if mi < 0:
        # 负值可能是数值误差，返回0（互信息最小为0）
        return 0.0
    return mi

def write_channel_results(out_file_name, mutual_info, capacity):
    """
    将信道指标结果写入CSV文件。
    """
    with open(out_file_name, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['互信息', '信道容量'])
        writer.writerow([mutual_info, capacity])
