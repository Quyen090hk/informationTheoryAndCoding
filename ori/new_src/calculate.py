"""
信道编解码指标计算模块
功能：计算信道编解码系统的性能指标
输入：编码前的文件、编码后的文件、解码后的文件
输出：包含性能指标的CSV文件（竖着显示数据）
指标：
  1. 压缩比（编码前文件字节数/编码后文件字节数）
  2. 误码率（汉明失真，错误数据比特/总数据比特）
  3. 编码前的信源信息传输率（信息比特/字节）
  4. 编码后的信源信息传输率（信息比特/字节）
"""

import csv
import os
import time

class ChannelCodingMetrics:
    """
    信道编解码指标计算类
    """

    def __init__(self, csv_file: str = "channel_coding_metrics.csv"):
        """
        初始化指标计算器
        """
        self.csv_file = csv_file

    def read_binary_file(self, file_path: str) -> tuple:
        """
        读取二进制文件并返回字节内容和比特串
        """
        try:
            with open(file_path, 'rb') as f:
                file_bytes = f.read()

            # 将字节转换为比特串
            bit_string = ''.join(f'{byte:08b}' for byte in file_bytes)

            return file_bytes, bit_string

        except FileNotFoundError:
            raise FileNotFoundError(f"文件不存在: {file_path}")
        except Exception as e:
            raise Exception(f"读取文件时出错: {e}")

    def read_text_bits_file(self, file_path: str) -> tuple:
        """
        读取纯文本比特文件（包含'0'和'1'字符的文件）
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            # 移除所有非0/1字符（如空格、换行、注释等）
            bit_string = ''.join(c for c in content if c in '01')

            return content.encode('utf-8'), bit_string

        except FileNotFoundError:
            raise FileNotFoundError(f"文件不存在: {file_path}")
        except Exception as e:
            raise Exception(f"读取文件时出错: {e}")

    def calculate_hamming_distance(self, bits1: str, bits2: str) -> tuple:
        """
        计算两个比特串之间的汉明距离（不同比特的数量）
        """
        # 确保两个比特串长度相同，如果不同则截断到较短的长度
        min_length = min(len(bits1), len(bits2))
        bits1 = bits1[:min_length]
        bits2 = bits2[:min_length]

        # 计算不同比特的数量
        distance = sum(1 for b1, b2 in zip(bits1, bits2) if b1 != b2)

        return distance, min_length

    def calculate_metrics(self, original_file: str, encoded_file: str, decoded_file: str) -> dict:
        """
        计算所有性能指标
        """
        print("\n" + "=" * 60)
        print("开始计算信道编解码指标...")
        print("=" * 60)

        # 读取原始文件
        print("\n1. 读取原始文件...")
        original_bytes, original_bits = self.read_binary_file(original_file)
        original_byte_count = len(original_bytes)
        original_bit_count = len(original_bits)

        print(f"   原始文件字节数: {original_byte_count}")
        print(f"   原始文件比特数: {original_bit_count}")

        # 读取编码文件
        print("\n2. 读取编码文件...")
        encoded_bytes, encoded_bits = self.read_text_bits_file(encoded_file)
        encoded_byte_count = len(encoded_bytes)
        encoded_bit_count = len(encoded_bits)

        print(f"   编码文件字节数: {encoded_byte_count}")
        print(f"   编码文件比特数: {encoded_bit_count}")

        # 读取解码文件
        print("\n3. 读取解码文件...")
        decoded_bytes, decoded_bits = self.read_binary_file(decoded_file)
        decoded_byte_count = len(decoded_bytes)
        decoded_bit_count = len(decoded_bits)

        print(f"   解码文件字节数: {decoded_byte_count}")
        print(f"   解码文件比特数: {decoded_bit_count}")

        # 计算压缩比
        print("\n4. 计算压缩比...")
        if encoded_byte_count > 0:
            compression_ratio = original_byte_count / encoded_byte_count
        else:
            compression_ratio = 0.0

        print(f"   压缩比 = 原始文件字节数 / 编码文件字节数")
        print(f"         = {original_byte_count} / {encoded_byte_count}")
        print(f"         = {compression_ratio:.4f}")

        # 计算误码率（汉明失真）
        print("\n5. 计算误码率...")
        hamming_distance, compared_bits = self.calculate_hamming_distance(original_bits, decoded_bits)

        if compared_bits > 0:
            bit_error_rate = hamming_distance / compared_bits
        else:
            bit_error_rate = 0.0

        print(f"   汉明距离（错误比特数）: {hamming_distance}")
        print(f"   比较的总比特数: {compared_bits}")
        print(f"   误码率 = {hamming_distance} / {compared_bits}")
        print(f"         = {bit_error_rate:.8f} ({bit_error_rate*100:.4f}%)")

        # 计算编码前的信源信息传输率
        print("\n6. 计算编码前的信源信息传输率...")
        if original_byte_count > 0:
            original_info_rate = original_bit_count / original_byte_count
        else:
            original_info_rate = 0.0

        print(f"   信息传输率 = 原始比特数 / 原始字节数")
        print(f"             = {original_bit_count} / {original_byte_count}")
        print(f"             = {original_info_rate:.4f} 比特/字节")

        # 计算编码后的信源信息传输率
        print("\n7. 计算编码后的信源信息传输率...")
        if encoded_byte_count > 0:
            encoded_info_rate = original_bit_count / encoded_byte_count
        else:
            encoded_info_rate = 0.0

        print(f"   信息传输率 = 原始比特数 / 编码文件字节数")
        print(f"             = {original_bit_count} / {encoded_byte_count}")
        print(f"             = {encoded_info_rate:.4f} 比特/字节")

        # 准备结果字典
        metrics = {
            'original_file': original_file,
            'encoded_file': encoded_file,
            'decoded_file': decoded_file,

            'original_byte_count': original_byte_count,
            'encoded_byte_count': encoded_byte_count,
            'decoded_byte_count': decoded_byte_count,

            'original_bit_count': original_bit_count,
            'encoded_bit_count': encoded_bit_count,
            'decoded_bit_count': decoded_bit_count,

            'compression_ratio': compression_ratio,
            'hamming_distance': hamming_distance,
            'compared_bits': compared_bits,
            'bit_error_rate': bit_error_rate,
            'original_info_rate': original_info_rate,
            'encoded_info_rate': encoded_info_rate,
        }

        # 保存结果到CSV（竖着显示）
        self._save_to_csv_vertical(metrics)

        # 打印汇总
        self._print_summary(metrics)

        return metrics

    def _save_to_csv_vertical(self, metrics: dict):
        """
        将计算结果保存到CSV文件（竖着显示数据）

        格式：
        指标名称,指标值
        """
        # 获取当前时间戳
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # 检查文件是否存在，如果不存在则创建并写入标题行
        file_exists = os.path.exists(self.csv_file)

        with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # 如果是第一次写入，添加标题行
            if not file_exists:
                writer.writerow(["信道编解码指标分析报告"])
                writer.writerow(["生成时间", timestamp])
                writer.writerow([])  # 空行
                writer.writerow(["指标类别", "指标名称", "指标值", "单位/说明"])

            # 写入空行作为分隔
            writer.writerow([])
            writer.writerow(["测试记录"])
            writer.writerow(["测试时间", timestamp])

            # 写入文件信息
            writer.writerow(["文件信息", "编码前的文件", metrics['original_file'], ""])
            writer.writerow(["文件信息", "编码后的文件", metrics['encoded_file'], ""])
            writer.writerow(["文件信息", "解码后的文件", metrics['decoded_file'], ""])
            writer.writerow([])  # 空行

            # 写入文件大小信息
            writer.writerow(["文件大小", "原始文件字节数", metrics['original_byte_count'], "字节"])
            writer.writerow(["文件大小", "原始文件比特数", metrics['original_bit_count'], "比特"])
            writer.writerow(["文件大小", "编码文件字节数", metrics['encoded_byte_count'], "字节"])
            writer.writerow(["文件大小", "编码文件比特数", metrics['encoded_bit_count'], "比特"])
            writer.writerow(["文件大小", "解码文件字节数", metrics['decoded_byte_count'], "字节"])
            writer.writerow(["文件大小", "解码文件比特数", metrics['decoded_bit_count'], "比特"])
            writer.writerow([])  # 空行

            # 写入性能指标
            writer.writerow(["性能指标", "压缩比", f"{metrics['compression_ratio']:.6f}",
                           f"原始文件大小/编码文件大小 = {metrics['original_byte_count']}/{metrics['encoded_byte_count']}"])

            writer.writerow(["性能指标", "误码率", f"{metrics['bit_error_rate']:.10f}",
                           f"错误比特数/总比特数 = {metrics['hamming_distance']}/{metrics['compared_bits']}"])

            writer.writerow(["性能指标", "编码前信源信息传输率", f"{metrics['original_info_rate']:.6f}",
                           f"原始比特数/原始字节数 = {metrics['original_bit_count']}/{metrics['original_byte_count']}"])

            writer.writerow(["性能指标", "编码后信源信息传输率", f"{metrics['encoded_info_rate']:.6f}",
                           f"原始比特数/编码文件字节数 = {metrics['original_bit_count']}/{metrics['encoded_byte_count']}"])

            writer.writerow([])  # 空行

            # 写入附加信息
            writer.writerow(["附加信息", "汉明距离", metrics['hamming_distance'], "不同比特的数量"])
            writer.writerow(["附加信息", "比较的总比特数", metrics['compared_bits'], "实际比较的比特数"])

            # 写入评估结果
            writer.writerow([])  # 空行
            writer.writerow(["评估结果", "传输质量",
                           "完美传输" if metrics['bit_error_rate'] == 0 else
                           "良好传输" if metrics['bit_error_rate'] < 0.01 else
                           "中等传输" if metrics['bit_error_rate'] < 0.1 else "较差传输",
                           f"误码率: {metrics['bit_error_rate']*100:.4f}%"])

            writer.writerow(["评估结果", "压缩效果",
                           "压缩" if metrics['compression_ratio'] > 1 else "扩展",
                           f"压缩比: {metrics['compression_ratio']:.4f}"])

        print(f"\n结果已保存到CSV文件: {self.csv_file}")
        print("数据格式: 竖着显示，每个指标占一行")

    def _print_summary(self, metrics: dict):
        """
        打印指标计算结果摘要
        """
        print("\n" + "=" * 60)
        print("信道编解码指标计算结果摘要")
        print("=" * 60)

        print(f"\n1. 文件大小信息:")
        print(f"   原始文件: {metrics['original_byte_count']} 字节, {metrics['original_bit_count']} 比特")
        print(f"   编码文件: {metrics['encoded_byte_count']} 字节, {metrics['encoded_bit_count']} 比特")
        print(f"   解码文件: {metrics['decoded_byte_count']} 字节, {metrics['decoded_bit_count']} 比特")

        print(f"\n2. 压缩性能:")
        print(f"   压缩比: {metrics['compression_ratio']:.4f}")
        if metrics['compression_ratio'] > 1:
            print(f"   (编码后文件比原始文件小 {metrics['compression_ratio']:.2f} 倍)")
        else:
            print(f"   (编码后文件比原始文件大 {1/metrics['compression_ratio']:.2f} 倍)")

        print(f"\n3. 误码率 (BER):")
        print(f"   汉明距离: {metrics['hamming_distance']} 比特")
        print(f"   误码率: {metrics['bit_error_rate']:.8f} ({metrics['bit_error_rate']*100:.4f}%)")

        if metrics['bit_error_rate'] == 0:
            print(f"   ✓ 完美传输: 无比特错误")
        elif metrics['bit_error_rate'] < 0.01:
            print(f"   ✓ 良好传输: 误码率低于1%")
        elif metrics['bit_error_rate'] < 0.1:
            print(f"   ⚠ 中等传输: 误码率低于10%")
        else:
            print(f"   ✗ 较差传输: 误码率高于10%")

        print(f"\n4. 信源信息传输率:")
        print(f"   编码前: {metrics['original_info_rate']:.4f} 比特/字节")
        print(f"   编码后: {metrics['encoded_info_rate']:.4f} 比特/字节")

        efficiency_change = ((metrics['encoded_info_rate'] - metrics['original_info_rate']) /
                            metrics['original_info_rate'] * 100 if metrics['original_info_rate'] > 0 else 0)

        if efficiency_change < 0:
            print(f"   编码后传输率降低了 {abs(efficiency_change):.2f}%")
        elif efficiency_change > 0:
            print(f"   编码后传输率提高了 {efficiency_change:.2f}%")
        else:
            print(f"   传输率没有变化")

        print("\n" + "=" * 60)

def clean_file_path(file_path: str) -> str:
    """
    清理文件路径：去除首尾的引号和空格
    """
    if not file_path:
        return ""

    # 去除首尾空格
    file_path = file_path.strip()

    # 去除首尾的引号
    if (file_path.startswith('"') and file_path.endswith('"')) or \
       (file_path.startswith("'") and file_path.endswith("'")):
        file_path = file_path[1:-1]

    return file_path

def main():
    """
    主函数：从控制台输入三个文件路径，计算性能指标
    """
    print("信道编解码指标计算模块")
    print("=" * 60)
    print("功能: 计算压缩比、误码率、信源信息传输率等指标")
    print("输出: 竖着显示数据的CSV文件")
    print("=" * 60)

    while True:
        print("\n请输入三个文件路径 (输入 'exit' 退出程序):")

        try:
            # 获取编码前的文件路径
            original_file = input("编码前的文件路径: ").strip()
            original_file = clean_file_path(original_file)

            if original_file.lower() in ('exit', 'quit', 'q'):
                print("程序已退出")
                break

            # 检查文件是否存在
            if not os.path.exists(original_file):
                print(f"错误: 文件 '{original_file}' 不存在")
                continue

            # 获取编码后的文件路径
            encoded_file = input("编码后的文件路径: ").strip()
            encoded_file = clean_file_path(encoded_file)

            if encoded_file.lower() in ('exit', 'quit', 'q'):
                print("程序已退出")
                break

            if not os.path.exists(encoded_file):
                print(f"错误: 文件 '{encoded_file}' 不存在")
                continue

            # 获取解码后的文件路径
            decoded_file = input("解码后的文件路径: ").strip()
            decoded_file = clean_file_path(decoded_file)

            if decoded_file.lower() in ('exit', 'quit', 'q'):
                print("程序已退出")
                break

            if not os.path.exists(decoded_file):
                print(f"错误: 文件 '{decoded_file}' 不存在")
                continue

            # 计算指标
            try:
                calculator = ChannelCodingMetrics()
                metrics = calculator.calculate_metrics(original_file, encoded_file, decoded_file)

                # 询问是否继续
                print("\n" + "-" * 40)
                continue_choice = input("是否继续计算其他文件? (y/n): ").strip().lower()
                if continue_choice != 'y':
                    print("程序已退出")
                    break

            except Exception as e:
                print(f"计算过程中出现错误: {e}")
                print("请检查文件格式是否正确。")
                continue_choice = input("\n是否重试? (y/n): ").strip().lower()
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

def view_csv_file():
    """
    查看CSV文件内容
    """
    csv_file = "channel_coding_metrics.csv"

    if not os.path.exists(csv_file):
        print(f"文件不存在: {csv_file}")
        return

    print(f"\n查看CSV文件内容: {csv_file}")
    print("=" * 60)

    with open(csv_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content)

if __name__ == "__main__":
    print("信道编解码指标计算模块")
    print("=" * 60)
    print("选择操作:")
    print("1. 计算指标")
    print("2. 查看CSV文件内容")

    try:
        choice = input("请输入选择 (1/2): ").strip()

        if choice == '1':
            main()
        elif choice == '2':
            view_csv_file()
        else:
            print("无效选择，运行计算指标模式")
            main()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        exit(0)