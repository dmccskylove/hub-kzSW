#!/bin/bash
# setup_cloud.sh — AutoDL 4090D 云端环境初始化（一次性）
# 用法：bash cloud/setup_cloud.sh
set -e
cd "$(dirname "$0")/.."
# AutoDL 非交互 shell 不加载 conda init，显式加 PATH
export PATH=/root/miniconda3/bin:$PATH
# 模型缓存放到数据盘 autodl-tmp（系统盘空间有限）；已有缓存需先迁移，见 USAGE_GUIDE
export HF_HUB_CACHE=/root/autodl-tmp/hf_cache/hub
mkdir -p "$HF_HUB_CACHE"

echo "===== [1/3] 安装依赖（trl 0.21 + transformers 5.5.3，参考项目验证组合）====="
pip install -q trl==0.21.0 transformers==5.5.3 peft==0.15.0 accelerate==1.5.2 datasets matplotlib

echo "===== [2/3] 配置 HF 镜像与 mmap 规避 ====="
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_MMAP=1
echo "请确认以下环境变量已写入 ~/.bashrc（run_cloud.sh 每次运行也会 export）：
  export HF_ENDPOINT=https://hf-mirror.com
  export HF_HUB_DISABLE_MMAP=1"

echo "===== [3/3] 预下载模型（避免训练中途卡下载）====="
python - <<'EOF'
from transformers import AutoModelForCausalLM, AutoTokenizer
for m in ["Qwen/Qwen2-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct"]:
    print("downloading", m)
    AutoTokenizer.from_pretrained(m)
    AutoModelForCausalLM.from_pretrained(m)  # 下载权重后进程退出即释放
print("模型就绪")
EOF

echo "===== 环境初始化完成 ====="
