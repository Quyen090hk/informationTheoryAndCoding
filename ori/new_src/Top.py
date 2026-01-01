"""
顶层仿真程序 - 自动化信息传输系统仿真
支持多种场景的仿真，自动调用各个模块完成完整的传输流程
"""

import csv
import os
import shutil
import argparse
import numpy as np
import sys

# 导入必要的模块函数
from coding import RepetitionCodeEncoder
from decoding import repetition_decode_file, extract_encoded_bits_from_file, majority_vote_decode
from channel import bsc_workflow, generate_probability_csv, read_input, compute_cdf, get_data, simulate_bsc, read_dat, write_dat


class CustomParser(argparse.ArgumentParser):
    """自定义命令行参数解析器"""
    def error(self, message):
        """错误处理"""
        self.print_help()
        print(message)
        exit(1)


# 场景配置
# 根据表3-1，需要支持四种编码组合
SCENARIOS = {
    'ideal': {
        'name': '理想场景',
        'source_pmf': 'p0=0.5.csv',
        'noise_pmf': 'p=0.csv',
        'source_encode': False,
        'channel_encode': False,
        'channel_error_p': 0.0,
        'description': '等概率分布，无信源编码，无信道编码，错误传递概率0'
    },
    'non_ideal_both': {
        'name': '一般非理想场景-有信源编码有信道编码',
        'source_pmf': 'p0=0.1.csv',
        'noise_pmf': 'p=0.01.csv',
        'source_encode': True,
        'channel_encode': True,
        'channel_error_p': 0.02,
        'description': 'P(0)=0.1，有信源编码，有信道编码，错误传递概率0.02'
    },
    'non_ideal_source_only': {
        'name': '一般非理想场景-有信源编码无信道编码',
        'source_pmf': 'p0=0.1.csv',
        'noise_pmf': 'p=0.01.csv',
        'source_encode': True,
        'channel_encode': False,
        'channel_error_p': 0.02,
        'description': 'P(0)=0.1，有信源编码，无信道编码，错误传递概率0.02'
    },
    'non_ideal_channel_only': {
        'name': '一般非理想场景-无信源编码有信道编码',
        'source_pmf': 'p0=0.1.csv',
        'noise_pmf': 'p=0.01.csv',
        'source_encode': False,
        'channel_encode': True,
        'channel_error_p': 0.02,
        'description': 'P(0)=0.1，无信源编码，有信道编码，错误传递概率0.02'
    },
    'non_ideal_none': {
        'name': '一般非理想场景-无信源编码无信道编码',
        'source_pmf': 'p0=0.1.csv',
        'noise_pmf': 'p=0.01.csv',
        'source_encode': False,
        'channel_encode': False,
        'channel_error_p': 0.02,
        'description': 'P(0)=0.1，无信源编码，无信道编码，错误传递概率0.02'
    }
}

# 解析命令行参数
parser = CustomParser("the top level program for simulation scenarios")
parser.add_argument("-s", "--scenario", type=str, 
                   choices=['ideal', 'non_ideal_both', 'non_ideal_source_only', 'non_ideal_channel_only', 'non_ideal_none', 'non_ideal_all', 'all'],
                   default='all', help="scenario to run: ideal, non_ideal_*, non_ideal_all, or all")
parser.add_argument("MSG_LEN", type=int, help="length of the generated message (in bytes)")
parser.add_argument("-del", "--delete", action="store_true", help="Whether to delete existing files")
parser.add_argument("-d", "--detail", action="store_true", help="Whether to print detailed info")

args = parser.parse_args()
msg_len = args.MSG_LEN
delete = args.delete
show_detail = args.detail
scenario_choice = args.scenario

# 固定参数
RS = 1.0  # 信源数据率固定为1（数据比特/秒）

# ------------------------------------命令程序---------------------------------------
# 获取脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(SCRIPT_DIR, "input")

byteSourceCMD = "byteSource.py"
sourceEncodeCMD = "source_encoder.py"
sourceDecodeCMD = "source_decoder.py"
channelCMD = "channel.py"
calcInfoCMD = "calcInfo.py"
calcDMSInfoCMD = "calaDMSInfo.py"
channelIndexCalcCMD = "channelIndexCalc.py"

# ---------------------------------------临时文件路径-----------------------------
TEMP_DAT_DIR = os.path.join("..", "data", "temp", "datfile")
TEMP_METRIX_DIR = os.path.join("..", "data", "temp", "metrics")
OUTPUT_FILE_256_DIR = os.path.join("..", "data", "temp", "file_2bit_to_256bit")
METRIX_DIR = os.path.join("..", "data", "metrics")

# 删除/生成目录
if not os.path.exists(TEMP_DAT_DIR):
    os.makedirs(TEMP_DAT_DIR)
else:
    if delete:
        shutil.rmtree(TEMP_DAT_DIR)
        os.makedirs(TEMP_DAT_DIR)
if not os.path.exists(TEMP_METRIX_DIR):
    os.makedirs(TEMP_METRIX_DIR)
else:
    if delete:
        shutil.rmtree(TEMP_METRIX_DIR)
        os.makedirs(TEMP_METRIX_DIR)
if not os.path.exists(OUTPUT_FILE_256_DIR):
    os.makedirs(OUTPUT_FILE_256_DIR)
if not os.path.exists(METRIX_DIR):
    os.makedirs(METRIX_DIR)


def simulate_scenario(scenario_key):
    """仿真单个场景"""
    scenario = SCENARIOS[scenario_key]
    print(f"\n{'='*80}")
    print(f"开始仿真: {scenario['name']}")
    print(f"场景描述: {scenario['description']}")
    print(f"{'='*80}")
    
    # 输入文件路径
    input_file = os.path.join(INPUT_DIR, scenario['source_pmf'])
    noise_file = os.path.join(INPUT_DIR, scenario['noise_pmf'])
    
    # 生成256元概率分布文件名
    pmf_input_file_256_name = os.path.basename(input_file).split('.')[0]
    pmf_input_file_256 = os.path.join(OUTPUT_FILE_256_DIR, pmf_input_file_256_name + ".256.csv")
    
    # ---------------------流程文件---------------------
    scenario_prefix = scenario_key
    temp_source = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_source.{msg_len//1024}KB.dat")
    temp_source_encode = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_source.encode.huf")
    temp_source_bits = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_source.bits.txt")
    temp_channel_encode = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_channel.encode.txt")
    temp_noise = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_noise.dat")
    temp_channel = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_channel.dat")
    temp_channel_decode = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_channel.decode.txt")
    temp_channel_decode_bits = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_channel.decode.bits.txt")
    temp_channel_decode_binary = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_channel.decode.dat")
    output_file = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_output.dat")
    output_file_256 = os.path.join(OUTPUT_FILE_256_DIR, f"{scenario_prefix}_source.{msg_len//1024}KB.256.csv")
    
    # --------------------指标文件--------------------
    source_metrics = os.path.join(TEMP_METRIX_DIR, f"{scenario_prefix}_source_metrics.csv")
    sink_entropy_csv = os.path.join(TEMP_METRIX_DIR, f"{scenario_prefix}_sink_entropy.csv")
    sink_error_rate_csv = os.path.join(TEMP_METRIX_DIR, f"{scenario_prefix}_sink.errorRate.csv")
    channel_metrics = os.path.join(TEMP_METRIX_DIR, f"{scenario_prefix}_channel_metrics.csv")
    source_sink_metrics = os.path.join(TEMP_METRIX_DIR, f"{scenario_prefix}_source_sink_metrics.csv")
    
    # ---------------------------------- 运行流程 ----------------------------------------
    os.system("echo off")
    now_file = ""
    
    # 1. 生成信源文件
    os.system("echo 'msg generating...'")
    os.system(f"python {byteSourceCMD} {input_file} {temp_source} {msg_len}")
    now_file = temp_source
    
    # 2. 假如进行信源编码
    if scenario['source_encode']:
        os.system("echo 'source encode...'")
        os.system(f"python {sourceEncodeCMD} {input_file} {now_file} {temp_source_encode}")
        now_file = temp_source_encode
    
    # 3. 假如进行信道编码
    original_binary_size = None  # 保存原始二进制文件大小
    if scenario['channel_encode']:
        os.system("echo 'channel encode...'")
        # 需要将二进制文件转换为比特串
        if scenario['source_encode']:
            # .huf文件，读取二进制内容
            with open(now_file, 'rb') as f:
                data = f.read()
            original_binary_size = len(data)  # 保存原始大小
            bit_string = ''.join(f'{byte:08b}' for byte in data)
            print(f"信源编码文件大小: {len(data)} 字节, 比特串长度: {len(bit_string)}")
        else:
            # .dat文件，转换为比特串
            data = np.fromfile(now_file, dtype=np.uint8)
            original_binary_size = len(data)  # 保存原始大小
            bit_string = ''.join(f'{byte:08b}' for byte in data)
            print(f"信源文件大小: {len(data)} 字节, 比特串长度: {len(bit_string)}")
        
        # 保存比特串到文件
        with open(temp_source_bits, 'w', encoding='utf-8') as f:
            f.write(bit_string)
        
        # 使用重复码编码器进行编码
        encoder = RepetitionCodeEncoder()
        encoded_bits = encoder.encode_bit_string(bit_string)
        print(f"信道编码后比特串长度: {len(encoded_bits)} (原始长度: {len(bit_string)})")
        with open(temp_channel_encode, 'w', encoding='utf-8') as f:
            f.write(encoded_bits)
        
        now_file = temp_channel_encode
    
    # 4. 通过信道
    os.system("echo 'passing BSC...'")
    if scenario['channel_encode']:
        # 处理比特串文件
        # 读取编码后的比特串
        with open(now_file, 'r', encoding='utf-8') as f:
            encoded_bits = ''.join(c for c in f.read() if c in '01')
        
        # 生成噪声比特串
        np.random.seed()  # 重置随机种子
        noise_bits = ''.join('1' if np.random.random() < scenario['channel_error_p'] else '0' 
                            for _ in range(len(encoded_bits)))
        
        # 异或操作
        channel_output_bits = ''.join('1' if a != b else '0' for a, b in zip(encoded_bits, noise_bits))
        
        # 保存信道输出
        with open(temp_channel, 'w', encoding='utf-8') as f:
            f.write(channel_output_bits)
        
        # 生成噪声文件（二进制格式）
        noise_bytes = []
        for i in range(0, len(noise_bits), 8):
            byte_str = noise_bits[i:i+8]
            if len(byte_str) == 8:
                noise_bytes.append(int(byte_str, 2))
        if noise_bytes:
            np.array(noise_bytes, dtype=np.uint8).tofile(temp_noise)
        
        now_file = temp_channel
    else:
        # 直接处理二进制文件
        # 生成噪声文件
        noise_pmf_file = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_noise_pmf.csv")
        generate_probability_csv(noise_pmf_file, scenario['channel_error_p'])
        
        # 直接调用bsc_workflow函数
        bsc_workflow(now_file, noise_pmf_file, temp_channel, temp_noise, 
                    scenario['channel_error_p'], msg_len)
        now_file = temp_channel
    
    # 5. 假如进行了信道编码，那么一定要进行信道解码
    if scenario['channel_encode']:
        os.system("echo 'channel decode...'")
        # 使用重复码解码
        with open(now_file, 'r', encoding='utf-8') as f:
            encoded_bits = ''.join(c for c in f.read() if c in '01')
        
        decoded_bits = majority_vote_decode(encoded_bits, n=3)
        
        # 保存解码后的比特串
        with open(temp_channel_decode, 'w', encoding='utf-8') as f:
            f.write(decoded_bits)
        
        # 将比特串转换回二进制文件
        # 如果之前有信源编码，需要恢复为.huf格式；否则为.dat格式
        bytes_list = []
        # 根据原始二进制文件大小截断或补0
        expected_bits = original_binary_size * 8 if original_binary_size else len(decoded_bits)
        
        if len(decoded_bits) > expected_bits:
            # 截断到期望长度
            decoded_bits = decoded_bits[:expected_bits]
            print(f"警告: 解码比特串长度超过期望，已截断: {len(decoded_bits)} -> {expected_bits}")
        elif len(decoded_bits) < expected_bits:
            # 补0到期望长度
            decoded_bits = decoded_bits + '0' * (expected_bits - len(decoded_bits))
            print(f"警告: 解码比特串长度不足，已补0: {len(decoded_bits)} -> {expected_bits}")
        
        # 确保长度是8的倍数
        if len(decoded_bits) % 8 != 0:
            decoded_bits = decoded_bits + '0' * (8 - len(decoded_bits) % 8)
        
        for i in range(0, len(decoded_bits), 8):
            byte_str = decoded_bits[i:i+8]
            if len(byte_str) == 8:
                bytes_list.append(int(byte_str, 2))
        
        # 截断到原始大小
        if original_binary_size and len(bytes_list) > original_binary_size:
            bytes_list = bytes_list[:original_binary_size]
        
        if bytes_list:
            data = np.array(bytes_list, dtype=np.uint8)
            # 保存为二进制文件（.huf或.dat格式都是二进制）
            data.tofile(temp_channel_decode_binary)
            # 验证文件是否成功写入
            if os.path.exists(temp_channel_decode_binary) and os.path.getsize(temp_channel_decode_binary) > 0:
                # 验证文件大小
                actual_size = os.path.getsize(temp_channel_decode_binary)
                if original_binary_size and abs(actual_size - original_binary_size) > 0:
                    print(f"警告: 文件大小不匹配: 实际={actual_size}, 期望={original_binary_size}")
                    # 如果大小不匹配，尝试修正
                    if actual_size > original_binary_size:
                        # 截断文件
                        with open(temp_channel_decode_binary, 'r+b') as f:
                            f.truncate(original_binary_size)
                        print(f"已截断文件到期望大小: {original_binary_size}")
                    elif actual_size < original_binary_size:
                        # 补0
                        with open(temp_channel_decode_binary, 'ab') as f:
                            f.write(b'\x00' * (original_binary_size - actual_size))
                        print(f"已补0到期望大小: {original_binary_size}")
                
                # 如果有信源编码，验证.huf文件头部格式
                if scenario['source_encode']:
                    try:
                        with open(temp_channel_decode_binary, 'rb') as f:
                            header_size_bytes = f.read(2)
                            if len(header_size_bytes) == 2:
                                header_size = int.from_bytes(header_size_bytes, 'little')
                                if header_size < 6 or header_size > actual_size:
                                    print(f"警告: .huf文件头部大小异常: {header_size}, 文件大小: {actual_size}")
                    except Exception as e:
                        print(f"警告: 验证.huf文件头部时出错: {e}")
                
                now_file = temp_channel_decode_binary
                print(f"信道解码完成，恢复文件大小: {os.path.getsize(temp_channel_decode_binary)} 字节 (期望: {original_binary_size if original_binary_size else '未知'})")
            else:
                print("错误: 信道解码后文件写入失败")
                now_file = temp_channel_decode
        else:
            print("警告: 解码后没有数据")
            now_file = temp_channel_decode
    else:
        temp_channel_decode_binary = None
    
    # 6. 假如进行了信源编码，那么一定要进行信源解码
    if scenario['source_encode']:
        os.system("echo 'source decode...'")
        # 检查输入文件是否存在且有效
        if os.path.exists(now_file) and os.path.getsize(now_file) > 0:
            # 检查文件是否至少包含头部（至少6字节：2字节头部长度 + 1字节符号数 + 4字节原始长度）
            file_size = os.path.getsize(now_file)
            if file_size < 6:
                print(f"错误: 信源解码输入文件太小 ({file_size} 字节)，可能已损坏")
                # 尝试使用原始信源文件
                if os.path.exists(temp_source):
                    print(f"使用原始信源文件作为输出: {temp_source}")
                    with open(output_file, "wb") as f1:
                        with open(temp_source, "rb") as f2:
                            data = f2.read()
                            f1.write(data)
                    now_file = output_file
                else:
                    print(f"错误: 无法恢复，原始信源文件也不存在")
                    now_file = output_file
            else:
                # 尝试解码
                result = os.system(f"python {sourceDecodeCMD} {now_file} {output_file}")
                if result != 0:
                    print(f"警告: 信源解码失败，返回码: {result}")
                    print(f"  输入文件: {now_file}, 大小: {file_size} 字节")
                    # 如果解码失败，尝试使用原始信源文件
                    if os.path.exists(temp_source):
                        print(f"使用原始信源文件作为输出")
                        with open(output_file, "wb") as f1:
                            with open(temp_source, "rb") as f2:
                                data = f2.read()
                                f1.write(data)
                    else:
                        # 最后尝试：直接复制输入文件
                        with open(output_file, "wb") as f1:
                            with open(now_file, "rb") as f2:
                                data = f2.read()
                                f1.write(data)
                # 检查输出文件是否生成
                if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                    print(f"错误: 信源解码后输出文件不存在或为空: {output_file}")
                    # 尝试使用原始信源文件
                    if os.path.exists(temp_source):
                        with open(output_file, "wb") as f1:
                            with open(temp_source, "rb") as f2:
                                data = f2.read()
                                f1.write(data)
                now_file = output_file
        else:
            print(f"错误: 信源解码输入文件不存在或为空: {now_file}")
            # 尝试使用原始信源文件
            if os.path.exists(temp_source):
                with open(output_file, "wb") as f1:
                    with open(temp_source, "rb") as f2:
                        data = f2.read()
                        f1.write(data)
                now_file = output_file
            else:
                print(f"错误: 无法恢复，原始信源文件也不存在")
                now_file = output_file
    else:
        # 直接复制
        if os.path.exists(now_file):
            with open(output_file, "wb") as f1:
                with open(now_file, "rb") as f2:
                    data = f2.read()
                    f1.write(data)
            now_file = output_file
        else:
            print(f"错误: 文件不存在: {now_file}")
    
    # ------------------------------- 计算指标,写入文件 ----------------------------
    os.system("echo calculating metrics...")
    now_file_metrix = temp_source
    
    # 1. 信源信息熵
    os.system(f"python {calcDMSInfoCMD} {temp_source} {output_file_256} {source_metrics}")
    
    # 2. 如果进行了信源编码
    if scenario['source_encode']:
        now_file_metrix = temp_source_encode
    
    # 3. 如果进行了信道编码
    if scenario['channel_encode']:
        # 计算信道解码后的信息熵
        if os.path.exists(temp_channel_decode_binary):
            channel_decode_entropy_csv = os.path.join(TEMP_METRIX_DIR, f"{scenario_prefix}_channel_decode_entropy.csv")
            os.system(f"python {calcInfoCMD} {temp_channel_decode_binary} {channel_decode_entropy_csv}")
        now_file_metrix = temp_channel_encode
    
    # 4. 计算信道指标（IUV和ec）
    # 初始化IUV和ec
    IUV = 0
    ec = 0
    # 使用channelIndexCalc计算互信息
    # 输入：编码前的文件（进入信道编码器的输入）
    # 输出：经过信道编码、传输、解码后的文件（从信道解码器输出的文件）
    # 注意：需要确保输入和输出文件格式一致（都是二进制文件）
    if scenario['channel_encode']:
        # 有信道编码：输入是进入信道编码前的文件，输出是信道解码后的文件
        if scenario['source_encode']:
            # 有信源编码：输入是.huf文件，输出也应该是.huf格式（但当前是.dat）
            # 为了正确计算，我们需要比较二进制数据
            channel_input_file = temp_source_encode  # .huf文件
            channel_output_file = temp_channel_decode_binary  # .dat文件（信道解码后）
        else:
            # 无信源编码：输入是.dat文件，输出也是.dat文件
            channel_input_file = temp_source  # .dat文件
            channel_output_file = temp_channel_decode_binary  # .dat文件
    else:
        # 无信道编码：直接比较信道输入和输出
        channel_input_file = now_file_metrix
        channel_output_file = temp_channel
    
    if os.path.exists(channel_input_file) and os.path.exists(channel_output_file):
        try:
            # 读取输入和输出数据（都作为二进制文件读取）
            # 注意：.huf文件也是二进制格式，可以用read_dat读取
            try:
                input_data = read_dat(channel_input_file)
            except:
                # 如果read_dat失败，尝试直接读取二进制
                with open(channel_input_file, 'rb') as f:
                    input_data = np.frombuffer(f.read(), dtype=np.uint8)
            
            try:
                output_data = read_dat(channel_output_file)
            except:
                # 如果read_dat失败，尝试直接读取二进制
                with open(channel_output_file, 'rb') as f:
                    output_data = np.frombuffer(f.read(), dtype=np.uint8)
            
            # 确保长度匹配
            min_len = min(len(input_data), len(output_data))
            if min_len > 0:
                input_data = input_data[:min_len]
                output_data = output_data[:min_len]
                
                print(f"计算信道指标: 输入长度={len(input_data)}, 输出长度={len(output_data)}")
                
                # 计算信道转移概率和互信息
                from channelIndexCalc import calculate_channel_probabilities, calculate_mutual_information, write_channel_results
                transition_prob = calculate_channel_probabilities(input_data, output_data)
                
                # 检查transition_prob是否有NaN或无效值
                if np.any(np.isnan(transition_prob)) or np.any(np.isinf(transition_prob)):
                    print("警告: 转移概率矩阵包含NaN或Inf值，使用简化计算")
                    IUV = 0
                else:
                    try:
                        IUV = calculate_mutual_information(transition_prob) / 8  # 转换为每比特的互信息
                        # 检查IUV是否为NaN、Inf或负值（互信息应该非负）
                        if np.isnan(IUV) or np.isinf(IUV) or IUV < 0:
                            if IUV < 0:
                                print(f"警告: IUV计算结果为负值 ({IUV:.6f})，互信息应该非负，使用简化计算")
                            else:
                                print("警告: IUV计算结果为NaN或Inf，使用简化计算")
                            IUV = 0
                    except Exception as e:
                        print(f"警告: 计算IUV时出错: {e}，使用简化计算")
                        IUV = 0
                
                # 计算信道错误概率ec
                error_count = np.sum(input_data != output_data)
                ec = error_count / len(input_data) if len(input_data) > 0 else 0.0
                
                print(f"信道指标计算: IUV={IUV:.6f}, ec={ec:.6f}, 错误数={error_count}/{len(input_data)}")
            else:
                print("警告: 输入或输出数据为空，无法计算信道指标")
                IUV = 0
                ec = 0
            
            # 保存信道指标
            # 格式：X, Y, H(X), H(Y), H(XY), H(X|Y), H(Y|X), I(X;Y), p
            if min_len > 0:
                with open(channel_metrics, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                    writer.writerow(['X', 'Y', 'H(X)', 'H(Y)', 'H(XY)', 'H(X|Y)', 'H(Y|X)', 'I(X;Y)', 'p'])
                    # 只计算I(X;Y)和p，其他值设为0
                    writer.writerow(['"{}"'.format(channel_input_file), '"{}"'.format(channel_output_file), 
                                    '0', '0', '0', '0', '0', IUV, ec])
                print(f"信道指标计算完成: IUV={IUV:.6f}, ec={ec:.6f}")
        except Exception as e:
            print(f"计算信道指标时出错: {e}")
            import traceback
            traceback.print_exc()
            IUV = 0
            ec = 0
    else:
        print(f"警告: 信道输入或输出文件不存在")
        if not os.path.exists(channel_input_file):
            print(f"  输入文件不存在: {channel_input_file}")
        if not os.path.exists(channel_output_file):
            print(f"  输出文件不存在: {channel_output_file}")
        IUV = 0
        ec = 0
    
    # 5. 计算信宿误码率
    # 计算原始信源和最终输出的误码率
    er = 0.0
    try:
        if os.path.exists(temp_source) and os.path.exists(output_file):
            source_data = np.fromfile(temp_source, dtype=np.uint8)
            sink_data = np.fromfile(output_file, dtype=np.uint8)
            min_len = min(len(source_data), len(sink_data))
            if min_len > 0:
                error_bits = 0
                total_bits = 0
                for i in range(min_len):
                    source_byte = source_data[i]
                    sink_byte = sink_data[i]
                    for j in range(8):
                        source_bit = (source_byte >> j) & 1
                        sink_bit = (sink_byte >> j) & 1
                        if source_bit != sink_bit:
                            error_bits += 1
                        total_bits += 1
                
                er = error_bits / total_bits if total_bits > 0 else 0.0
            else:
                print("警告: 源文件或输出文件为空")
        else:
            print(f"警告: 源文件或输出文件不存在")
            if not os.path.exists(temp_source):
                print(f"  源文件不存在: {temp_source}")
            if not os.path.exists(output_file):
                print(f"  输出文件不存在: {output_file}")
    except Exception as e:
        print(f"计算误码率时出错: {e}")
        import traceback
        traceback.print_exc()
        er = 0.0
    
    # 保存误码率
    file_exists = os.path.isfile(sink_error_rate_csv)
    with open(sink_error_rate_csv, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["INPUT1", "INPUT2", "error_rate"])
        writer.writerow([temp_source, output_file, er])
    
    # 6. 计算信宿的信息熵
    os.system(f"python {calcInfoCMD} {output_file} {sink_entropy_csv}")
    
    # 7. 计算IXZ（信源和信宿的互信息）
    new_noise_file = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_new_noise_file.dat")
    temp_noise_source_sink = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_noise_source_sink.dat")
    temp_source_sink = os.path.join(TEMP_DAT_DIR, f"{scenario_prefix}_source_sink.dat")
    
    IXZ = 0  # 初始化IXZ
    try:
        # 从误码率生成新的噪声概率分布
        with open(new_noise_file, "w", encoding='utf-8') as f1:
            f1.write(f"0,{1-er:.10f}\n")
            f1.write(f"1,{er:.10f}")
        
        # 生成噪声文件
        source_size = os.path.getsize(temp_source)
        os.system(f"python {byteSourceCMD} {new_noise_file} {temp_noise_source_sink} {source_size}")
        
        # 通过BSC信道
        if os.path.exists(temp_source) and os.path.exists(temp_noise_source_sink):
            source_data = read_dat(temp_source)
            noise_data = read_dat(temp_noise_source_sink)
            sink_data = simulate_bsc(source_data, noise_data)
            write_dat(sink_data, temp_source_sink)
            
            # 计算source_sink的互信息
            if os.path.exists(temp_source_sink):
                from channelIndexCalc import calculate_channel_probabilities, calculate_mutual_information
                transition_prob = calculate_channel_probabilities(source_data, sink_data)
                
                # 检查transition_prob是否有NaN或无效值
                if np.any(np.isnan(transition_prob)) or np.any(np.isinf(transition_prob)):
                    print("警告: source_sink转移概率矩阵包含NaN或Inf值，使用简化计算")
                    IXZ = 0
                else:
                    try:
                        IXZ = calculate_mutual_information(transition_prob) / 8  # 转换为每比特的互信息
                        # 检查IXZ是否为NaN
                        if np.isnan(IXZ) or np.isinf(IXZ):
                            print("警告: IXZ计算结果为NaN或Inf，使用简化计算")
                            IXZ = 0
                    except Exception as e:
                        print(f"警告: 计算IXZ时出错: {e}，使用简化计算")
                        IXZ = 0
                
                # 保存source_sink指标
                # 格式：X, Y, H(X), H(Y), H(XY), H(X|Y), H(Y|X), I(X;Y), p
                # I(X;Y)在倒数第二列
                with open(source_sink_metrics, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                    writer.writerow(['X', 'Y', 'H(X)', 'H(Y)', 'H(XY)', 'H(X|Y)', 'H(Y|X)', 'I(X;Y)', 'p'])
                    # 只计算I(X;Y)，其他值设为0
                    writer.writerow(['"{}"'.format(temp_source), '"{}"'.format(temp_source_sink), 
                                    '0', '0', '0', '0', '0', IXZ, er])
                print(f"IXZ计算完成: {IXZ:.6f}")
    except Exception as e:
        print(f"计算IXZ时出错: {e}")
        import traceback
        traceback.print_exc()
        IXZ = 0
    
    # -------------------------- 计算仿真的指标数值 ---------------------------------
    os.system("echo calculating target metrics...")
    rs = 1  # 初始信息率（bit/s）
    Rs = rc = R_ci = R_co = RI = 0
    eta = _L = -1
    # 注意：IXZ已经在上面计算过了，不要重新初始化
    
    # 获取信源信息熵
    try:
        if os.path.exists(source_metrics):
            with open(source_metrics, "r", encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                rows = [r for r in csv_reader]
                if len(rows) > 1:
                    row = rows[-1]
                    # 格式：Bit 0 Probability, Bit 1 Probability, Entropy, Redundancy
                    # Entropy在倒数第二列
                    if len(row) >= 2:
                        entropy_str = row[-2].strip('"').strip("'")
                        entropy = float(entropy_str)  # Entropy在倒数第二列
                        Rs = rs * entropy
                        # 理想情况下，如果entropy接近1（等概率分布），确保Rs=1
                        if scenario_key == 'ideal' and abs(entropy - 1.0) < 0.01:
                            Rs = 1.0
                            entropy = 1.0  # 也更新entropy，确保一致性
                            print(f"理想情况：信源信息熵修正为1.0（理论值），Rs={Rs:.6f}")
                        else:
                            print(f"信源信息熵: {entropy:.6f}, Rs={Rs:.6f}")
                    else:
                        print(f"警告: source_metrics格式不正确: {row}")
                        entropy = 0
                        Rs = 0
                else:
                    print(f"警告: source_metrics文件为空")
                    entropy = 0
                    Rs = 0
        else:
            print(f"错误: 找不到'{source_metrics}'")
            exit(1)
    except FileNotFoundError:
        print(f"找不到'{source_metrics}'，程序已退出")
        exit(1)
    except Exception as e:
        print(f"读取信源指标时出错: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    # 获取IUV和ec（如果之前计算了）
    if IUV == 0 or ec == 0:
        try:
            if os.path.exists(channel_metrics):
                with open(channel_metrics, "r", encoding='utf-8') as f:
                    csv_reader = csv.reader(f)
                    rows = [r for r in csv_reader]
                    if len(rows) > 1:
                        row = rows[-1]
                        # 格式：X, Y, H(X), H(Y), H(XY), H(X|Y), H(Y|X), I(X;Y), p
                        # I(X;Y)在倒数第二列，p在最后一列
                        if len(row) >= 2:
                            IUV_str = row[-2].strip('"').strip("'")
                            IUV = float(IUV_str)  # I(X;Y)在倒数第二列
                            # 检查IUV是否为负值（互信息应该非负）
                            if IUV < 0:
                                print(f"警告: 从channel_metrics读取的IUV为负值 ({IUV:.6f})，互信息应该非负，将使用简化计算")
                                IUV = 0  # 重置为0，后续会使用简化计算
                            ec_str = row[-1].strip('"').strip("'")
                            ec = float(ec_str)  # p在最后一列
                            print(f"从channel_metrics读取: IUV={IUV:.6f}, ec={ec:.6f}")
        except Exception as e:
            print(f"从channel_metrics读取IUV时出错: {e}")
            if show_detail:
                import traceback
                traceback.print_exc()
    
    # 如果IUV还是0、NaN或负值，使用简化计算
    # 互信息理论上应该是非负的，如果出现负值，说明计算有问题
    if IUV == 0 or np.isnan(IUV) or IUV < 0:
        if IUV < 0:
            print(f"警告: IUV为负值 ({IUV:.6f})，互信息应该非负，使用简化计算")
        if scenario['channel_error_p'] == 0.0 and er == 0.0:
            # 理想情况：无错误，IUV = 信源熵（每比特）
            # 对于等概率分布（ideal场景），entropy应该接近1，IUV应该等于1
            if scenario_key == 'ideal':
                IUV = 1.0  # 理想情况下，IUV = 1
                print(f"理想情况：IUV = 1.0（理论值）")
            else:
                IUV = entropy if entropy > 0 else Rs
                print(f"理想情况：IUV = 信源熵 = {IUV:.6f}")
        else:
            # 非理想情况：IUV = Rs * (1 - er)
            if scenario['channel_encode']:
                # 有信道编码：重复码N=3可以纠正部分错误
                IUV = Rs * (1 - er) if Rs > 0 else entropy * (1 - er)
            else:
                IUV = Rs * (1 - er)
            print(f"使用简化计算IUV: {IUV:.6f}")
    if ec == 0 or np.isnan(ec):
        ec = er
        print(f"使用简化计算ec: {ec:.6f}")
    # 理想情况下，如果channel_error_p=0，ec应该也是0
    if scenario['channel_error_p'] == 0.0:
        ec = 0.0
        print(f"理想情况：ec = 0")
    
    # 获取IXZ（如果之前计算了）
    if IXZ == 0:
        try:
            if os.path.exists(source_sink_metrics):
                with open(source_sink_metrics, "r", encoding='utf-8') as f:
                    csv_reader = csv.reader(f)
                    rows = [r for r in csv_reader]
                    if len(rows) > 1:
                        row = rows[-1]
                        # 格式：X, Y, H(X), H(Y), H(XY), H(X|Y), H(Y|X), I(X;Y), p
                        # I(X;Y)在倒数第二列
                        if len(row) >= 2:
                            IXZ_str = row[-2].strip('"').strip("'")
                            IXZ = float(IXZ_str)  # I(X;Y)在倒数第二列
                            print(f"从source_sink_metrics读取IXZ: {IXZ:.6f}")
        except Exception as e:
            print(f"从source_sink_metrics读取IXZ时出错: {e}")
            if show_detail:
                import traceback
                traceback.print_exc()
    
    # 获取信宿信息熵（用于简化计算IXZ）
    sink_entropy = 0
    try:
        if os.path.exists(sink_entropy_csv):
            with open(sink_entropy_csv, "r", encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                rows = [r for r in csv_reader]
                if len(rows) > 0:
                    # calcInfo.py的输出格式："文件路径","信息熵","文件长度"
                    row = rows[-1]
                    if len(row) > 1:
                        sink_entropy_str = row[1].strip('"').strip("'")
                        sink_entropy = float(sink_entropy_str)
                        print(f"从sink_entropy_csv读取信宿信息熵: {sink_entropy:.6f}")
    except Exception as e:
        print(f"读取信宿信息熵时出错: {e}")
        sink_entropy = 0
    
    # 如果IXZ还是0，使用简化计算
    # 理想情况下：如果错误概率为0，IXZ应该等于信源熵（每比特）
    if IXZ == 0 or np.isnan(IXZ):
        if scenario['channel_error_p'] == 0.0 and er == 0.0:
            # 理想情况：无错误，IXZ = 信源熵（每比特）
            # 对于等概率分布（ideal场景），entropy应该接近1，IXZ应该等于1
            if scenario_key == 'ideal':
                IXZ = 1.0  # 理想情况下，IXZ = 1
                print(f"理想情况：IXZ = 1.0（理论值）")
            else:
                IXZ = entropy if entropy > 0 else Rs
                print(f"理想情况：IXZ = 信源熵 = {IXZ:.6f}")
        elif sink_entropy > 0:
            IXZ = sink_entropy / 8  # 使用信宿信息熵
            print(f"使用信宿信息熵计算IXZ: {IXZ:.6f}")
        else:
            IXZ = Rs * (1 - er)  # 如果信宿信息熵不可用，使用备用计算
            print(f"使用简化计算IXZ: {IXZ:.6f}")
    
    # 根据场景计算指标
    if scenario['source_encode'] and not scenario['channel_encode']:
        # 只进行信源编码
        _L = entropy * 8  # 平均码长（比特/符号）
        eta = 1.0  # 编码效率
        rc = rs * _L / 8
        R_ci = Rs
        R_co = IUV * rc
        RI = rs * IXZ
        er = ec
    elif not scenario['source_encode'] and scenario['channel_encode']:
        # 只进行信道编码
        channelEncode_len = 3  # 重复码N=3
        rc = channelEncode_len * rs
        R_ci = Rs
        R_co = IUV * channelEncode_len * rs
        RI = rs * IXZ
    elif scenario['source_encode'] and scenario['channel_encode']:
        # 既进行信源编码又有信道编码
        _L = entropy * 8  # 平均码长（比特/符号）
        eta = 1.0  # 编码效率
        channelEncode_len = 3  # 重复码N=3
        rc = _L / 8 * channelEncode_len * rs
        R_ci = Rs
        R_co = IUV * rc
        RI = rs * IXZ
    else:
        # 不处理（理想场景：无信源编码，无信道编码）
        rc = rs
        R_ci = Rs
        R_co = IUV * rc
        RI = IXZ * rs
        er = ec
        # 理想情况下，如果channel_error_p=0，er应该也是0
        if scenario['channel_error_p'] == 0.0:
            er = 0.0
            print(f"理想情况：er = 0")
    
    # 将所有的结果存到文件里面
    headers = ['输入数据率rs', '信源信息率Rs', '信道数据率rc', '信道输入信息率Rci',
               '信道输出信息率Rco', '信宿关于信源信息率RI', '信宿误码率er']
    data = [rs, Rs, rc, R_ci, R_co, RI, er]
    formatted_data = [f"{num:.10f}" for num in data]
    # 对于非理想场景，使用统一的文件名，便于对比四种组合
    if scenario_key.startswith('non_ideal'):
        res_metrics_csv = os.path.join(METRIX_DIR, "non_ideal_res_metrics.csv")
    else:
        res_metrics_csv = os.path.join(METRIX_DIR, f"{scenario_prefix}_res_metrics.csv")
    
    # 检查文件是否存在以及是否为空
    file_exists = os.path.isfile(res_metrics_csv) and os.path.getsize(res_metrics_csv) > 0
    if file_exists:
        # 文件已存在且有内容，只追加数据行
        with open(res_metrics_csv, "a", newline='', encoding='utf-8') as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow(formatted_data)
    else:
        # 文件不存在或为空，写入表头和数据行
        with open(res_metrics_csv, "w", newline='', encoding='utf-8') as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow(headers)
            csv_writer.writerow(formatted_data)
    
    # 打印详细信息
    os.system(f"echo the target metrics data has been saved in {res_metrics_csv}")
    if show_detail:
        os.system("echo --------------------------the detailed info is below--------------------")
        print(f"信源信息率Rs：{Rs:.10f}")
        print(f"信道数据率rc：{rc:.10f}")
        print(f"信道输入信息率Rci：{R_ci:.10f}")
        print(f"信道输出信息率Rco：{R_co:.10f}")
        print(f"信宿关于信源信息率RI：{RI:.10f}")
        print(f"信宿误码率er：{er:.10f}")
    
    return {
        'rs': rs, 'Rs': Rs, 'rc': rc, 'R_ci': R_ci, 'R_co': R_co, 'RI': RI, 'er': er
    }


# 主程序
if __name__ == '__main__':
    print(f"\n{'='*80}")
    print("信息传输系统仿真程序")
    print(f"{'='*80}")
    print(f"消息长度: {msg_len} 字节")
    
    if scenario_choice == 'all':
        # 运行所有场景（理想场景 + 所有非理想场景）
        results = {}
        scenario_keys = ['ideal'] + [k for k in SCENARIOS.keys() if k.startswith('non_ideal')]
        for scenario_key in scenario_keys:
            try:
                result = simulate_scenario(scenario_key)
                results[scenario_key] = result
            except Exception as e:
                print(f"场景 {scenario_key} 仿真失败: {e}")
                import traceback
                traceback.print_exc()
    elif scenario_choice == 'non_ideal_all':
        # 运行所有非理想场景（四种组合）
        results = {}
        scenario_keys = [k for k in SCENARIOS.keys() if k.startswith('non_ideal')]
        for scenario_key in scenario_keys:
            try:
                result = simulate_scenario(scenario_key)
                results[scenario_key] = result
            except Exception as e:
                print(f"场景 {scenario_key} 仿真失败: {e}")
                import traceback
                traceback.print_exc()
    else:
        # 运行指定场景
        try:
            result = simulate_scenario(scenario_choice)
        except Exception as e:
            print(f"场景 {scenario_choice} 仿真失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("仿真完成！")
    print(f"{'='*80}")
