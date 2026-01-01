"""
信道解码模块 - 重复码解码器 (N=3)
功能：读取信道编码模块的输出文件，使用多数投票原则进行解码
输入：解码前的文件（格式与信道编码模块的输出文件相同）
输出：解码后的文件
原理：对每3个比特进行多数投票，选择出现次数最多的值作为解码结果
"""

import os
import re

def clean_file_path(file_path):
    """
    清理文件路径：去除首尾的引号、空格，并修正路径分隔符

    参数:
        file_path: 原始文件路径字符串

    返回:
        str: 清理后的文件路径
    """
    if not file_path:
        return ""

    # 去除首尾空格
    file_path = file_path.strip()

    # 去除首尾的引号
    if (file_path.startswith('"') and file_path.endswith('"')) or \
       (file_path.startswith("'") and file_path.endswith("'")):
        file_path = file_path[1:-1]

    # 修正路径分隔符（将反斜杠替换为正斜杠，或根据系统调整）
    # Windows路径中反斜杠需要转义或使用原始字符串
    # 这里保留原始输入，但去除多余的引号

    return file_path

def extract_encoded_bits_from_file(input_file):
    """
    从输入文件中提取编码后的比特序列

    参数:
        input_file: 输入文件路径

    返回:
        str: 提取的编码后比特序列
    """
    try:
        # 先清理文件路径
        input_file = clean_file_path(input_file)

        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError as e:
        print(f"文件未找到错误: {e}")
        return ""
    except PermissionError as e:
        print(f"权限错误: {e}")
        return ""
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return ""

    # 方法1：查找"编码后的完整比特序列"部分
    if "编码后的完整比特序列" in content:
        # 找到该部分之后的内容
        start_idx = content.find("编码后的完整比特序列") + len("编码后的完整比特序列")

        # 提取该行之后直到下一个标题或文件结束的内容
        remaining_content = content[start_idx:]

        # 提取所有0和1字符
        bits = ''.join([c for c in remaining_content if c in '01'])

        if bits:
            print(f"从'编码后的完整比特序列'部分提取到 {len(bits)} 个比特")
            return bits

    # 方法2：查找纯比特序列（没有空格的连续0和1）
    # 使用正则表达式查找连续的0和1
    bit_patterns = re.findall(r'[01]+', content)
    if bit_patterns:
        # 找出最长的连续比特串（最可能是编码后的比特序列）
        longest_bits = max(bit_patterns, key=len)
        if len(longest_bits) >= 10:  # 假设至少有10个比特才是有效的编码序列
            print(f"找到连续比特串，长度: {len(longest_bits)}")
            return longest_bits

    # 方法3：提取文件中所有的0和1字符
    all_bits = ''.join([c for c in content if c in '01'])
    if all_bits:
        print(f"提取所有0/1字符，得到 {len(all_bits)} 个比特")
        return all_bits

    print("警告: 无法从文件中提取比特序列")
    return ""

def majority_vote_decode(encoded_bits, n=3):
    """
    使用多数投票原则进行重复码解码

    参数:
        encoded_bits: 编码后的比特串
        n: 重复次数，固定为3

    返回:
        str: 解码后的比特串
    """
    if not encoded_bits:
        raise ValueError("编码比特串为空")

    if len(encoded_bits) % n != 0:
        print(f"警告: 编码比特串长度 {len(encoded_bits)} 不是{n}的整数倍")
        # 截断到最接近的n的倍数
        truncated_length = (len(encoded_bits) // n) * n
        encoded_bits = encoded_bits[:truncated_length]
        print(f"已截断为 {len(encoded_bits)} 个比特")

    decoded_bits = []

    # 每n个比特为一组进行解码
    for i in range(0, len(encoded_bits), n):
        group = encoded_bits[i:i+n]

        # 统计0和1的个数
        count_0 = group.count('0')
        count_1 = group.count('1')

        # 多数投票：选择出现次数多的比特
        if count_0 > count_1:
            decoded_bits.append('0')
        elif count_1 > count_0:
            decoded_bits.append('1')
        else:
            # 平票情况，按照约定选择0
            decoded_bits.append('0')

    return ''.join(decoded_bits)

def repetition_decode_file(input_file, output_file):
    """
    信道解码主函数

    参数:
        input_file: 输入文件路径（信道编码模块的输出文件）
        output_file: 输出文件路径（解码结果）
    """
    # 清理文件路径
    input_file_clean = clean_file_path(input_file)
    output_file_clean = clean_file_path(output_file)

    print(f"开始信道解码...")
    print(f"输入文件: {input_file_clean}")

    # 检查输入文件是否存在
    if not os.path.exists(input_file_clean):
        print(f"错误: 输入文件 '{input_file_clean}' 不存在")
        print(f"当前工作目录: {os.getcwd()}")
        print(f"尝试列出当前目录文件:")
        try:
            files = os.listdir('.')
            print(f"  当前目录文件: {files}")
        except:
            pass
        return ""

    try:
        # 1. 从输入文件中提取编码后的比特序列
        encoded_bits = extract_encoded_bits_from_file(input_file_clean)

        if not encoded_bits:
            print("错误: 无法从输入文件中提取有效的比特序列")
            return ""

        print(f"提取的编码比特数: {len(encoded_bits)}")

        # 2. 使用多数投票原则进行解码
        decoded_bits = majority_vote_decode(encoded_bits, n=3)

        print(f"解码后比特数: {len(decoded_bits)}")

        # 3. 将解码结果写入输出文件
        with open(output_file_clean, 'w', encoding='utf-8') as f:
            # 写入解码信息
            f.write("# ====================================\n")
            f.write("# 信道解码模块输出文件\n")
            f.write("# 解码方案: 重复码多数投票解码 (N=3)\n")
            f.write("# ====================================\n\n")

            # 写入解码参数
            f.write("# 解码参数\n")
            f.write(f"输入文件: {input_file_clean}\n")
            f.write(f"输出文件: {output_file_clean}\n")
            f.write(f"提取的编码比特数: {len(encoded_bits)}\n")
            f.write(f"解码后比特数: {len(decoded_bits)}\n")
            f.write(f"解码算法: 多数投票 (每3个比特为一组)\n\n")

            # 写入解码示例（显示前5组）
            if len(decoded_bits) > 0:
                f.write("# 解码示例（前5组）\n")
                for i in range(min(5, len(decoded_bits))):
                    group_start = i * 3
                    group_end = group_start + 3
                    if group_end <= len(encoded_bits):
                        group = encoded_bits[group_start:group_end]
                        count_0 = group.count('0')
                        count_1 = group.count('1')
                        decision = decoded_bits[i]
                        f.write(f"组{i+1}: {group} -> 0出现{count_0}次, 1出现{count_1}次 -> 解码为: {decision}\n")
                f.write("\n")

            # 写入解码后的比特序列
            f.write("# 解码后的比特序列\n")
            # 每80个比特换行，便于阅读
            for i in range(0, len(decoded_bits), 80):
                f.write(decoded_bits[i:i+80] + '\n')

        print(f"解码完成！")
        print(f"输出文件: {output_file_clean}")

        # 4. 显示解码统计信息
        print(f"\n解码统计:")
        print(f"  输入比特数: {len(encoded_bits)}")
        print(f"  输出比特数: {len(decoded_bits)}")
        print(f"  解码组数: {len(encoded_bits) // 3}")

        # 显示解码示例
        if len(decoded_bits) >= 3:
            print(f"\n解码示例（前3组）:")
            for i in range(min(3, len(decoded_bits))):
                group_start = i * 3
                group_end = group_start + 3
                if group_end <= len(encoded_bits):
                    group = encoded_bits[group_start:group_end]
                    decoded_bit = decoded_bits[i]
                    count_0 = group.count('0')
                    count_1 = group.count('1')
                    print(f"  组{i+1}: {group} -> 0:{count_0}, 1:{count_1} -> 解码: {decoded_bit}")

        return decoded_bits

    except ValueError as e:
        print(f"值错误: {e}")
    except Exception as e:
        print(f"解码过程中出现未知错误: {e}")
        import traceback
        traceback.print_exc()

    return ""

def main():
    """
    主函数：提供简单的用户交互界面
    """
    print("信道解码模块 - 重复码解码器 (N=3)")
    print("=" * 60)
    print("说明: 请输入信道编码模块的输出文件路径进行解码")
    print("提示: 可以直接输入文件路径，也可以拖拽文件到命令行")
    print("=" * 60)

    while True:
        try:
            input_file = input("\n请输入输入文件路径（或输入 'exit' 退出）: ").strip()

            # 清理输入的文件路径
            input_file_clean = clean_file_path(input_file)

            if input_file_clean.lower() in ('exit', 'quit', 'q'):
                print("程序已退出")
                break

            if not input_file_clean:
                print("错误: 输入不能为空")
                continue

            # 检查文件是否存在
            if not os.path.exists(input_file_clean):
                print(f"错误: 文件 '{input_file_clean}' 不存在")
                # 尝试使用原始输入（可能包含引号）作为路径
                if input_file != input_file_clean and os.path.exists(input_file):
                    print(f"使用原始输入路径: {input_file}")
                    input_file_clean = input_file
                else:
                    continue

            # 生成默认的输出文件名
            if '.' in input_file_clean:
                name_without_ext = input_file_clean.rsplit('.', 1)[0]
                output_file = name_without_ext + '_decoded.txt'
            else:
                output_file = input_file_clean + '_decoded.txt'

            # 询问用户是否使用默认输出文件名
            custom_output = input(f"输出文件路径 [默认: {output_file}]: ").strip()
            if custom_output:
                output_file = custom_output

            # 执行解码
            repetition_decode_file(input_file_clean, output_file)

            # 询问是否继续
            continue_choice = input("\n是否继续解码其他文件? (y/n): ").strip().lower()
            if continue_choice != 'y':
                print("程序已退出")
                break

        except KeyboardInterrupt:
            print("\n程序被用户中断")
            break
        except Exception as e:
            print(f"发生错误: {e}")
            continue_choice = input("\n是否继续? (y/n): ").strip().lower()
            if continue_choice != 'y':
                break

if __name__ == "__main__":
    main()