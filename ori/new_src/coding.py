"""
信道编码模块 - 重复码编码器 (N=3)
功能：从文件读取二进制比特串，进行重复编码，将结果保存到txt文件
输入：包含二进制比特串的文件路径
输出：编码后的比特串保存到txt文件
原理：每个比特重复3次，增加冗余以提高可靠性
"""

import os
import re
from datetime import datetime

def clean_file_path(file_path):
    """
    清理文件路径：去除首尾的引号、空格，并修正路径分隔符
    """
    if not file_path:
        return ""

    # 去除首尾空格
    file_path = file_path.strip()

    # 去除首尾的引号
    if (file_path.startswith('"') and file_path.endswith('"')) or \
       (file_path.startswith("'") and file_path.endswith("'")):
        file_path = file_path[1:-1]

    # 修正可能的多余空格
    file_path = file_path.replace('\\ ', '\\').replace('/ ', '/')

    # 修复常见的路径问题
    file_path = file_path.replace('"', '').replace("'", "")

    # 处理Windows路径中的反斜杠转义问题
    file_path = os.path.normpath(file_path)

    return file_path

class RepetitionCodeEncoder:
    """
    重复码编码器（N=3）
    """

    def __init__(self):
        """
        初始化编码器
        重复码的码长固定为N=3
        """
        self.N = 3  # 重复码的码长固定为3
        self.encoding_rate = 1/3  # 编码率 = 1/N

    def validate_bit_string(self, bit_string: str) -> bool:
        """
        验证输入是否为有效的二进制比特串
        """
        if not bit_string:
            return False

        return all(c in '01' for c in bit_string)

    def encode_bit_string(self, bit_string: str) -> str:
        """
        对比特串进行重复编码
        """
        # 验证输入
        if not self.validate_bit_string(bit_string):
            raise ValueError("输入必须为二进制比特串（仅包含0和1）")

        # 对每个比特重复3次
        encoded_bits = ''.join(bit * self.N for bit in bit_string)
        return encoded_bits

    def read_bit_string_from_file(self, file_path: str) -> str:
        """
        从文件中读取比特串
        """
        # 先清理文件路径
        file_path = clean_file_path(file_path)

        print(f"尝试读取文件: {file_path}")
        print(f"当前工作目录: {os.getcwd()}")

        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                # 尝试列出当前目录文件，帮助调试
                print(f"文件 '{file_path}' 不存在")
                print("尝试列出当前目录文件:")
                try:
                    current_dir = os.getcwd()
                    files = os.listdir(current_dir)
                    print(f"当前目录 ({current_dir}) 中的文件:")
                    for f in files:
                        print(f"  - {f}")
                except:
                    pass
                raise FileNotFoundError(f"文件不存在: {file_path}")

            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # 提取所有0和1字符
            bit_string = ''.join(c for c in content if c in '01')

            if not bit_string:
                raise ValueError("文件中没有找到有效的二进制比特（0或1）")

            print(f"成功读取文件，找到 {len(bit_string)} 个比特")
            return bit_string

        except FileNotFoundError as e:
            raise e
        except Exception as e:
            raise Exception(f"读取文件时出错: {e}")

    def save_encoded_result(self, original_bits: str, encoded_bits: str,
                           input_file_path: str, output_file_path: str = None) -> str:
        """
        将编码结果保存到txt文件
        """
        # 清理输入和输出文件路径
        input_file_path = clean_file_path(input_file_path)

        # 如果未指定输出文件路径，根据输入文件生成
        if output_file_path is None:
            base_name = os.path.splitext(os.path.basename(input_file_path))[0]
            output_file_path = f"{base_name}_encoded.txt"
        else:
            output_file_path = clean_file_path(output_file_path)

        # 确保文件扩展名为.txt
        if not output_file_path.endswith('.txt'):
            output_file_path += '.txt'

        # 写入文件
        with open(output_file_path, 'w', encoding='utf-8') as f:
            # 写入编码信息
            f.write("# ====================================\n")
            f.write("# 信道编码模块输出文件\n")
            f.write("# 编码方案: 重复码 (N=3)\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 输入文件: {input_file_path}\n")
            f.write("# ====================================\n\n")

            # 写入编码参数
            f.write("# 编码参数\n")
            f.write(f"编码类型: 重复码 (Repetition Code)\n")
            f.write(f"码长 (N): {self.N}\n")
            f.write(f"编码率: 1/{self.N} ({self.encoding_rate:.4f})\n")
            f.write(f"原始比特数: {len(original_bits)}\n")
            f.write(f"编码后比特数: {len(encoded_bits)}\n")
            f.write(f"扩展因子: {self.N}倍\n\n")

            # 写入原始比特序列
            f.write("# 1. 原始比特序列\n")
            # 每80个比特换行，便于阅读
            for i in range(0, len(original_bits), 80):
                f.write(original_bits[i:i+80] + '\n')
            f.write('\n')

            # 写入编码示例（显示前10个比特的编码）
            f.write("# 2. 编码示例\n")
            f.write("# 格式: [原始比特] -> [3比特码字]\n")
            for i in range(min(10, len(original_bits))):
                original_bit = original_bits[i]
                encoded_bit_group = encoded_bits[i*3:(i+1)*3]
                f.write(f"比特 {i+1}: {original_bit} -> {encoded_bit_group}\n")
            f.write('\n')

            # 写入编码后的完整比特序列
            f.write("# 3. 编码后的完整比特序列\n")
            # 每3个比特（一个码字）加一个空格便于阅读
            formatted_encoded = ' '.join([encoded_bits[i:i+3] for i in range(0, len(encoded_bits), 3)])
            # 每10个码字换行
            groups = formatted_encoded.split(' ')
            for i in range(0, len(groups), 10):
                line = ' '.join(groups[i:i+10])
                f.write(line + '\n')

        return output_file_path

def main():
    """
    主函数：提供用户交互界面
    """
    print("信道编码模块 - 重复码编码器 (N=3)")
    print("=" * 60)
    print("功能: 从文件读取二进制比特串，进行重复编码，保存结果到txt文件")
    print("说明:")
    print("  1. 输入包含二进制比特串的文件路径")
    print("  2. 文件内容应为只包含0和1的文本")
    print("  3. 可以直接输入路径，或者拖拽文件到命令行")
    print("  4. 输入 'exit' 或 'quit' 退出程序")
    print("=" * 60)

    encoder = RepetitionCodeEncoder()

    while True:
        try:
            print("\n" + "-" * 40)
            # 获取输入文件路径
            input_file_path = input("请输入输入文件路径: ").strip()

            # 检查退出条件
            if input_file_path.lower() in ('exit', 'quit', 'q'):
                print("程序已退出")
                break

            # 清理文件路径
            input_file_path_clean = clean_file_path(input_file_path)

            if not input_file_path_clean:
                print("错误：输入不能为空")
                continue

            print(f"清理后的文件路径: {input_file_path_clean}")

            try:
                # 从文件读取比特串
                original_bits = encoder.read_bit_string_from_file(input_file_path_clean)

                print(f"读取成功！")
                print(f"原始比特串长度: {len(original_bits)}")

                # 显示部分内容
                if len(original_bits) > 20:
                    print(f"前20位: {original_bits[:20]}...")
                else:
                    print(f"内容: {original_bits}")

                print(f"开始编码...")

                # 执行编码
                encoded_result = encoder.encode_bit_string(original_bits)
                print(f"编码完成！")
                print(f"编码后比特数: {len(encoded_result)}")
                print(f"长度变化: {len(original_bits)} → {len(encoded_result)} (扩展{encoder.N}倍)")

                # 显示编码示例
                if len(original_bits) >= 3:
                    print(f"\n编码示例（前3个比特）:")
                    for i in range(min(3, len(original_bits))):
                        original_bit = original_bits[i]
                        encoded_bits = encoded_result[i*3:(i+1)*3]
                        print(f"  比特 {i+1}: {original_bit} -> {encoded_bits}")

                # 询问输出文件路径
                base_name = os.path.splitext(os.path.basename(input_file_path_clean))[0]
                default_output = f"{base_name}_encoded.txt"
                output_file_path = input(f"\n请输入输出文件路径 [默认: {default_output}]: ").strip()

                if not output_file_path:
                    output_file_path = default_output

                try:
                    saved_file = encoder.save_encoded_result(original_bits, encoded_result,
                                                           input_file_path_clean, output_file_path)
                    print(f"✓ 编码结果已保存到文件: {saved_file}")

                    # 显示文件信息
                    file_size = os.path.getsize(saved_file)
                    print(f"  文件大小: {file_size} 字节")

                    # 显示文件绝对路径
                    abs_path = os.path.abspath(saved_file)
                    print(f"  绝对路径: {abs_path}")

                except Exception as e:
                    print(f"保存文件时出错: {e}")

            except FileNotFoundError as e:
                print(f"文件不存在: {e}")
                print("请检查文件路径是否正确")
                continue
            except ValueError as e:
                print(f"文件内容错误: {e}")
                print("请确保文件内容只包含0和1字符")
                continue
            except Exception as e:
                print(f"处理文件时出错: {e}")
                continue

            # 询问是否继续
            continue_choice = input("\n是否继续编码其他文件? (y/n): ").strip().lower()
            if continue_choice != 'y':
                print("程序已退出")
                break

        except KeyboardInterrupt:
            print("\n程序被用户中断")
            break
        except Exception as e:
            print(f"未知错误: {e}")

if __name__ == "__main__":
    main()