
import os
import sys
import numpy as np
import csv
from calcInfo import compute_info
def read_byte_dat(file_path):
    """
    读取 byte.dat 文件并生成 2 元 DMS 信源的概率分布。
    """
    with open(file_path, 'rb') as f:
        data = f.read()

    # 统计每个字节出现的次数
    byte_counts = np.zeros(256, dtype=int)
    for byte in data:
        byte_counts[byte] += 1

    # 计算每种字节的概率
    total_bytes = len(data)
    symbol_prob_2bit = byte_counts / total_bytes

    return symbol_prob_2bit

def DMS_2bit_from_byte_dat(file_byte_dat, out_file_256):
    """
    从 byte.dat 文件生成 256 元概率分布，并保存到 CSV 文件。
    """
    # 读取 byte.dat 文件并生成 2 元 DMS 信源的概率分布
    symbol_prob_2bit = read_byte_dat(file_byte_dat)

    # 保存 256 元概率分布到输出文件
    with open(out_file_256, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        for i in range(256):
            csv_writer.writerow([i, symbol_prob_2bit[i]])

    return symbol_prob_2bit

def calculate_binary_probabilities(file_256):
    """
    计算数据比特概率。
    """
    count_0_p = np.zeros(256)
    count_1_p = np.zeros(256)
    P = np.zeros(256)

    with open(file_256, newline='') as in_file:
        csv_reader = csv.reader(in_file)
        for i, row in enumerate(csv_reader):
            symbol = int(row[0])
            probability = float(row[1])
            binary = format(symbol, '08b')  # 获取 8 位二进制表示
            count_1 = binary.count('1')
            count_0 = 8 - count_1
            count_0_p[i] = count_0 / 8
            count_1_p[i] = count_1 / 8
            P[i] = probability

    binary_p = np.zeros(2)
    binary_p[0] = np.sum(P * count_0_p)
    binary_p[1] = np.sum(P * count_1_p)

    return binary_p[0], binary_p[1]

def calculate_entropy(probabilities):
    """
    计算信息熵。
    """
    entropy = -np.sum(probabilities * np.log2(probabilities))
    return entropy

def calculate_redundancy(probabilities):
    """
    计算信源冗余度。
    """
    entropy = calculate_entropy(probabilities)
    max_entropy = -np.sum(np.array([1 / len(probabilities)] * len(probabilities)) * np.log2(
        np.array([1 / len(probabilities)] * len(probabilities))))
    redundancy = 1 - (entropy / max_entropy)
    return redundancy

def main(input_file, output_file_256, output_file_info):
    """
    主函数：处理输入文件并生成输出文件。
    """
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist.")
        sys.exit(1)

    # 从 byte.dat 文件生成 256 元概率分布文件
    symbol_prob_2bit = DMS_2bit_from_byte_dat(input_file, output_file_256)

    # 计算数据比特概率
    binary_p0, binary_p1 = calculate_binary_probabilities(output_file_256)

    # 计算信息熵和信源冗余度
    # entropy = calculate_entropy(np.array([binary_p0, binary_p1]))
    file_ndarray = np.fromfile(input_file, dtype=np.uint8)
    entropy = round(compute_info(file_ndarray)/8,10)
    redundancy = calculate_redundancy(np.array([binary_p0, binary_p1]))
    headers = ['Bit 0 Probability','Bit 1 Probability','Entropy','Redundancy']
    data = [binary_p0,binary_p1,entropy,redundancy]
    # 保存数据比特概率、信息熵和信源冗余度到 CSV 文件
    file_exists = os.path.isfile(output_file_info)
    if file_exists:
        with open(output_file_info, 'a', newline='') as info_file:
            csv_writer = csv.writer(info_file)
            csv_writer.writerow(data)
    else:
        with open(output_file_info, 'w', newline='') as info_file:
            csv_writer = csv.writer(info_file)
            csv_writer.writerow(headers)
            csv_writer.writerow(data)


        # csv_writer.writerow(['Data', 'Value'])
        # csv_writer.writerow(['Bit 0 Probability', binary_p0])
        # csv_writer.writerow(['Bit 1 Probability', binary_p0])
        # csv_writer.writerow(['Entropy', entropy])
        # csv_writer.writerow(['Redundancy', redundancy])


    # print(f"256-bit probability distribution saved to: {output_file_256}")
    # print(f"Data bit probabilities, entropy, and redundancy saved to: {output_file_info}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python calaDMSInfo.py <input_file.dat> <output_file_256.csv> <output_file_info.csv>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file_256 = sys.argv[2]
    output_file_info = sys.argv[3]

    main(input_file, output_file_256, output_file_info)